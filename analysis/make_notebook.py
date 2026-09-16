# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["nbformat", "nbclient", "ipykernel", "nbconvert", "pymc==5.28.5", "arviz==0.23.4", "pandas==2.3.2", "numpy==2.2.6", "scipy>=1.13,<2", "matplotlib>=3.9,<4"]
# ///
"""Create and execute the companion notebook, with saved tables and figures."""
import json
import os
from pathlib import Path
import sys

import nbformat as nbf
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager
from nbconvert import HTMLExporter

OUT = Path(__file__).resolve().parent
os.environ.setdefault("IPYTHONDIR", str(OUT / ".ipython"))
os.environ.setdefault("MPLCONFIGDIR", str(OUT / ".mpl"))
kernel_dir = OUT / ".kernels" / "python3"
kernel_dir.mkdir(parents=True, exist_ok=True)
(kernel_dir / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
    "display_name": "Data centres analysis", "language": "python"}))

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# County data centres: fresh audit and a 2030 scenario

## Summary

This notebook recomputes the existing dashboard, applies **three confirmed county-election corrections** to a separate analysis snapshot, and simulates the tracked pipeline at two-year intervals from 2026 to 2036. **2030 is the main horizon.**

The original 7.2× intensity gap is a description of reported targets in selected host counties. The simulated trajectory includes uncertain missing sizes, approval, delivery and phased buildout. Every project belongs entirely to its county's 2024 winner; every resident in that county has the same modelled capacity-per-resident value.

**The forecast intervals are conditional on the stated assumptions.** The dataset cannot estimate a causal relationship between Trump support and local approval. Unknown capacity is estimated with distributions, not silently converted into reported measurements. Even the 2026 operating-capacity baseline is modelled because an operational site's reported MW may describe future phases.
"""),
md("""## Context & methods

### Key assumptions

- Political grouping: the county's 2024 presidential winner; this does not establish the permitting authority or the preferences of every resident.
- Proposed-project approval: probability equals the county's Trump share of **all presidential votes**. Compare with 50% everywhere and an assumed 75%/25% winner step.
- Post-approval realization: a separate Beta(8,2) factor, mean 80%. Permitted and construction-stage projects use mean eventual realization probabilities of 80% and 95% respectively. Cancelled projects contribute zero; operational sites remain open.
- Median time until first operation: four years for proposals, three for permitted projects, two for construction. Add project and shared schedule uncertainty. All dates refer to September 15; 2030 is four years from the snapshot.
- At first operation, 10–30% of the target opens. Remaining capacity ramps over a size-dependent period. Operational projects start at a Beta(8,2) fraction of target; this is an explicit baseline assumption.
- County residents are counted once. Primary intensity uses the fixed union of non-cancelled tracked host counties, including zero-capacity counties in a draw; the alternative denominator includes only counties operating in that draw. Both use 2024 population.
- No untracked future announcements, retirements, population growth, changes of county political label, electricity demand constraint or national grid capacity constraint are forecast. This is a projection of the retained pipeline.

### Capacity model

For each reported project, `log(MW)` is Normal with a shared intercept, partially pooled stage/operator effects, and a standardized log-acreage predictor. Missing acreage is analytically integrated under a standard Normal assumption on the standardized scale; it is not filled as an observed value. Feature scaling is fitted only on training rows. Posterior predictive draws estimate the 214 missing sizes. Politics is not a predictor of size. Unknown-MW draws are conditioned on a declared 0.1–10,000 MW range; halving/doubling unknown sizes tests sensitivity to non-random disclosure. Reported MW stays fixed as a **target**, with a separate half-target scenario.

For project i in county c: operating MW at time t = target MW × realization indicator × buildout fraction(t). County intensity = sum of operating project MW / county population × 1,000. County host-resident count = population × indicator(any project operating), summed once per county.

Implementation and all priors: [pipeline_model.py](pipeline_model.py). Fresh-source audit and exact calculations: [audit_numbers.py](audit_numbers.py). Official election corrections and provenance: [election_corrections.json](election_corrections.json).
"""),
code("""from pathlib import Path
import json, sys, io, contextlib
import pandas as pd
from IPython.display import display, Image

out = Path.cwd()
if not (out / 'pipeline_model.py').exists():
    out = out / 'analysis'
sys.path.insert(0, str(out))
from audit_numbers import audit
from pipeline_model import run

# Reconcile retained downloads; no network required for this notebook.
with contextlib.redirect_stdout(io.StringIO()):
    audit_result = audit()
    results = run(draws=1000, tune=2000)
model = json.loads((out / 'model_summary.json').read_text())
diagnostics = json.loads((out / 'model_diagnostics.json').read_text())
print(model['checks'])
"""),
md("""## Data: fresh audit

The live Brockovich feed was fetched anew and still has 474 projects, updated September 5, 2026. The Census Vintage 2024 population file was fetched anew. All retained project fields match the feed, and all 303 populated county joins match Census. This establishes reproduction of the chosen snapshot, rather than independent verification of each project announcement.

The independent election comparison covers 302 of 304 host counties. The McGovern/Fox compilation is an independent cross-check, not certified final results. Harvard's direct MIT download returned HTTP 400; an older MIT mirror was inspected, found to have its own location/reporting-unit issues, and was **not adopted wholesale**.

Official returns confirm that DeKalb, Illinois and Jackson, Missouri were incorrectly labelled Trump-won. Jackson needs its separately reported Kansas City election jurisdiction included. El Paso, Colorado had Elbert's vote counts. Four projects receive these three county corrections in the analysis snapshot. The website source snapshot is retained separately.

Twenty project location fields disagree, and the manual North Slope vote result remains unverified. Original MW also mixes campus targets, phases, and generation projects. A separate scenario excludes uncertain locations, North Slope, and projects labelled 'rumored'.
"""),
code("""rows = []
for scope in ['all', 'operational', 'under_construction', 'permitted', 'proposed', 'cancelled']:
    for winner, group in audit_result['corrected_scopes'][scope]['groups'].items():
        rows.append({'Scope': scope, 'County winner': winner, 'Projects': group['projects'],
                     'MW known': group['mw_known'], 'Reported target GW': group['reported_mw']/1000,
                     'Known-MW host population': group['capacity_population'],
                     'Reported MW / 1,000': group['mw_per_1000']})
display(pd.DataFrame(rows).round(3))

comparison = []
for label, key in [('Original snapshot', 'scopes'), ('Confirmed election corrections', 'corrected_scopes')]:
    s = audit_result[key]['all']; g = s['groups']
    comparison.append({'Version': label, 'Trump projects': g['Trump']['projects'],
                       'Harris projects': g['Harris']['projects'],
                       'Trump MW / 1,000': g['Trump']['mw_per_1000'],
                       'Harris MW / 1,000': g['Harris']['mw_per_1000'],
                       'Ratio': g['Trump']['mw_per_1000']/g['Harris']['mw_per_1000']})
display(pd.DataFrame(comparison).round(3))
display(pd.DataFrame(audit_result['corrected_scopes']['all']['groups']).T
        [['projects','mw_known','reported_mw','investment_known','reported_investment','host_counties','host_population']])
"""),
md("""### Recomputed weighting cards

These indices answer different questions. Capacity-weighted vote shares split project weight between candidates; the winner-take-all intensity measure assigns the entire project to a county winner. Capacity × population does not measure either per-resident infrastructure or unique residents affected, so it is not used as the model's outcome.
"""),
code("""display(pd.DataFrame(audit_result['corrected_scopes']['all']['weighting_cards']).T.round(3))
display(pd.DataFrame(audit_result['geography_disagreements']))
"""),
md("""## Results: size model checks

Four chains are checked for convergence and divergences. A fixed random 20% sample, stratified by stage, is withheld before fitting the validation model. Prediction intervals include variation between individual projects and parameter uncertainty. A holdout of reported projects cannot validate assumptions about projects that never disclose MW.
"""),
md("""### PyMC hierarchy printout

PyMC's direct Graphviz export is retained as [capacity_model.dot](capacity_model.dot), with a rendered hierarchy diagram below. The printout is the exact DOT source emitted by the fitted model, so the hierarchy remains inspectable even if a local Graphviz renderer is unavailable.

![PyMC model hierarchy](capacity_model.svg)
"""),
code("""from IPython.display import Code
print((out / 'capacity_model.dot').read_text())
"""),
code("""display(pd.DataFrame({k:v for k,v in diagnostics.items() if k in ['holdout','full']}).T)
display(pd.Series(diagnostics['holdout_prediction'], name='Held-out validation'))
display(Image(filename=str(out / 'model_validation.png')))
"""),
md("""Adding acreage improves typical individual prediction error to about 1.76×, versus 2.58× for a stage-median baseline. However, **aggregate validation fails on this split**: the 52 withheld projects total 32.66 GW, while the model predicts a median of 57.43 GW and a 90% interval of 43.86–72.71 GW. Individual 90% intervals cover 45/52 projects (86.5%).

This is a material upward-bias warning for aggregate imputation. The operating-GW outputs below are exploratory scenarios, not a calibrated forecast. Halving and doubling unknown sizes explicitly probes this problem, but cannot prove the base estimate correct. Wide predictive intervals remain necessary, especially for projects with neither MW nor acreage disclosed. One held-out split does not establish performance on undisclosed projects.
"""),
code("""estimates = pd.read_csv(out / 'project_capacity_estimates.csv')
display(estimates[estimates.capacity_basis.eq('model estimate')]
        [['name','status','county_winner','capacity_mw_p05','capacity_mw_median','capacity_mw_p95']]
        .sort_values('capacity_mw_median', ascending=False).head(12).round(1))
display(pd.Series({'Missing target GW: 5th / median / 95th': model['unknown_total_gw_p05_median_p95'],
                   'Target GW per listed proposal: 5th / median / 95th': model['proposed_target_gw_per_location_p05_median_p95']}))
"""),
md("""### Two-year trajectory, with 2030 as the main horizon

The model sums joint simulation draws before taking quantiles. It never adds project medians or interval endpoints to produce aggregate intervals. Primary rates keep the same host-county population across years and scenarios, preventing changing denominators from masquerading as capacity growth.
"""),
code("""base = results[results.political.eq('proportional') & results.missing_multiplier.eq(1) &
               results.time_multiplier.eq(1) & results.target_multiplier.eq(1) &
               ~results.county_shared & ~results.exclude_flagged]
display(base[base.measure.eq('operating_gw')][['year','winner','p05','median','p95']].round(1))
display(Image(filename=str(out / 'pipeline_timeline.png')))
display(base[base.year.eq(2030)][['winner','measure','p05','median','p95','fixed_population']].round(3))
"""),
md("""### Sensitivity checks

These comparisons vary one assumption at a time with common random numbers. Interval width does not incorporate every possible model choice. The political-effect comparison applies only to proposals; projects already permitted or under construction use stage-based completion assumptions.

The exclusion scenario holds the original non-cancelled host-county denominator fixed. It is a stress test of whether questionable projects drive the result, not a corrected geography dataset. Halving reported pipeline targets also changes size-dependent ramp time, as specified in the model.
"""),
code("""display(results[results.year.eq(2030) & results.measure.eq('intensity_ratio')]
        .drop(columns=['winner','measure','fixed_population','year']).round(3))
display(Image(filename=str(out / 'scenario_sensitivity.png')))
"""),
md("""## Takeaways

1. Winner-take-all county grouping with equal resident accounting is a coherent scenario definition. It already describes the original intensity card's grouping, but it is different from splitting MW by vote share.
2. The fresh source review finds actual election errors; it also identifies incomplete MW coverage and mixed capacity definitions. Source agreement alone is insufficient validation.
3. Use the 2030 simulation as an assumption-driven scenario. The size posterior is empirically fitted; approval and schedule relationships are assumed. Keep both the neutral and proportional political scenarios visible.
4. Individual unknown sizes need wide intervals. The empirical validation does not justify presenting one filled-in MW number as a fact.
5. A production forecast should incorporate phase-specific target dates and capacity, resolved county locations, and a historical cohort of proposals with approval, cancellation, and operation dates. The current cross-sectional stage counts cannot estimate those transition probabilities.

### Reproduction and sources

Run `python3 analysis/audit_numbers.py --refresh` to refresh public source downloads. Run `uv run analysis/pipeline_model.py` to fit or reuse a validated matching posterior and rerun scenarios. Run `uv run analysis/make_notebook.py` to regenerate this executed notebook and its HTML view.

Source URLs, retrieval times and hashes are in [sources/manifest.json](sources/manifest.json). The three primary election documents are linked in [election_corrections.json](election_corrections.json). Capacity source notes and per-project links remain in [sources/projects.json](sources/projects.json). [PyMC documentation](https://www.pymc.io/projects/examples/en/latest/howto/Missing_Data_Imputation.html) explains posterior imputation; [MIT Election Lab](https://electionlab.mit.edu/data) documents the county election dataset and coverage. Trump administration support for data-centre permitting is documented in the [July 2025 White House fact sheet](https://www.whitehouse.gov/fact-sheets/2025/07/fact-sheet-president-donald-j-trump-accelerates-federal-permitting-of-data-center-infrastructure/); it does not supply county approval probabilities.
"""),
]
notebook = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
nbf.validate(notebook)
client = NotebookClient(notebook, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(OUT)}},
                        kernel_manager_class="jupyter_client.manager.KernelManager")
client.km = client.create_kernel_manager()
client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[str(OUT / ".kernels")])
client.execute()
nbf.write(notebook, OUT / "county_pipeline_review.ipynb")
exporter = HTMLExporter(template_name="lab")
html, _ = exporter.from_notebook_node(notebook)
(OUT / "county_pipeline_review.html").write_text(html)
assert all(c.get("execution_count") is not None for c in notebook.cells if c.cell_type == "code")
assert not any(o.output_type == "error" for c in notebook.cells if c.cell_type == "code" for o in c.outputs)
print("Executed and saved county_pipeline_review.ipynb and county_pipeline_review.html")
