# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["pymc==5.28.5", "arviz==0.23.4", "pandas==2.3.2", "numpy==2.2.6", "scipy>=1.13,<2", "matplotlib>=3.9,<4"]
# ///
"""Bayesian capacity imputation + explicit county pipeline scenarios, 2026–2036.

Run: uv run analysis/pipeline_model.py
The posterior estimates missing MW. Approval/timing assumptions are not fitted
or presented as empirical causal estimates. Original dashboard values stay intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import arviz as az
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymc as pm
from scipy.special import ndtr, ndtri

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"
SEED = 20260915
YEARS = [2026, 2028, 2030, 2032, 2034, 2036]
STAGES = ["operational", "under_construction", "permitted", "proposed", "cancelled"]
PARTIES = ["Trump", "Harris"]
COLORS = {"Trump": "#b91c1c", "Harris": "#1d4ed8"}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def operator_group(value):
    value = str(value or "").lower()
    for group, aliases in {"Amazon": ["amazon", "aws"], "Google": ["google"], "Microsoft": ["microsoft"],
                           "Meta": ["meta", "facebook"], "QTS": ["qts"], "Vantage": ["vantage"],
                           "Digital Realty": ["digital realty"]}.items():
        if any(alias in value for alias in aliases):
            return group
    return "Other"


def load_data():
    data = pd.read_json(OUT / "audited_facilities.json")
    source = json.loads((OUT / "sources/projects.json").read_text())
    metadata = {r["id"]: r for r in source["fac"]}
    data["confidence"] = data.id.map(lambda i: metadata[i]["cf"])
    data["source_notes"] = data.id.map(lambda i: metadata[i].get("nt", ""))
    data["operator_group"] = data.operator.map(operator_group)
    data["stage_idx"] = pd.Categorical(data.status, categories=STAGES).codes
    groups = sorted(data.operator_group.unique())
    data["operator_idx"] = pd.Categorical(data.operator_group, categories=groups).codes
    assert data.id.is_unique and data.mw.dropna().gt(0).all()
    assert data.county_winner.isin(PARTIES).all()
    assert data.trump_pct.between(0, 100).all()
    return data, groups


def fit_capacity(data, groups, train_mask, draws, tune, seed):
    """Partial pooling by stage and operator; politics is not a size predictor.

    A Gaussian distribution on log(MW) accommodates the large right tail.
    Predictive draws for missing values are later conditioned on a declared
    0.1–10,000 MW range; reported values are never clipped or replaced.
    """
    # Fit feature scaling only on training rows. Missing log-acreage is integrated
    # analytically as N(0,1) on this standardized scale, rather than filled as fact.
    known_area = np.log(data.loc[train_mask & data.acres.notna(), "acres"].to_numpy())
    area_center, area_scale = float(np.mean(known_area)), float(np.std(known_area))
    selected = data.loc[train_mask]
    x_area = ((np.log(selected.acres) - area_center) / area_scale).fillna(0).to_numpy()
    area_missing = selected.acres.isna().to_numpy().astype(float)
    with pm.Model(coords={"stage": STAGES, "operator": groups}) as model:
        intercept = pm.Normal("intercept", mu=np.log(300), sigma=2)
        stage_sd = pm.HalfNormal("stage_sd", sigma=1)
        operator_sd = pm.HalfNormal("operator_sd", sigma=1)
        stage_z = pm.Normal("stage_z", 0, 1, dims="stage")
        operator_z = pm.Normal("operator_z", 0, 1, dims="operator")
        stage_effect = pm.Deterministic("stage_effect", stage_z * stage_sd, dims="stage")
        operator_effect = pm.Deterministic("operator_effect", operator_z * operator_sd, dims="operator")
        area_effect = pm.Normal("area_effect", mu=0.7, sigma=0.7)
        sigma = pm.HalfNormal("sigma", sigma=1.5)
        mu = intercept + stage_effect[selected.stage_idx.to_numpy()] + operator_effect[selected.operator_idx.to_numpy()] + area_effect*x_area
        effective_sigma = pm.math.sqrt(sigma**2 + area_missing*area_effect**2)
        pm.Normal("log_mw", mu, effective_sigma, observed=np.log(selected.mw.to_numpy()))
        idata = pm.sample(draws=draws, tune=tune, chains=4, cores=2, target_accept=0.995,
                          random_seed=seed, progressbar=False, compute_convergence_checks=True)
        # PyMC's direct model printout: a Graphviz DOT representation of the
        # hierarchy, saved even when the system `dot` renderer is unavailable.
        try:
            (OUT / "capacity_model.dot").write_text(pm.model_to_graphviz(model).source)
        except Exception as exc:
            (OUT / "capacity_model.dot").write_text(f"// Graphviz export unavailable: {exc}\\n")
    idata.attrs["area_center"] = area_center
    idata.attrs["area_scale"] = area_scale
    return idata


def predict_capacity(idata, data, seed=SEED, cap=10000):
    posterior = idata.posterior.stack(sample=("chain", "draw"))
    intercept = posterior.intercept.values[:, None]
    stage = posterior.stage_effect.transpose("sample", "stage").values[:, data.stage_idx]
    operator = posterior.operator_effect.transpose("sample", "operator").values[:, data.operator_idx]
    x_area = ((np.log(data.acres) - idata.attrs["area_center"]) / idata.attrs["area_scale"]).fillna(0).to_numpy()
    area_beta = posterior.area_effect.values[:, None]
    mu = intercept + stage + operator + area_beta*x_area[None, :]
    sigma = posterior.sigma.values[:, None]
    sigma = np.sqrt(sigma**2 + data.acres.isna().to_numpy()[None, :]*area_beta**2)
    rng = np.random.default_rng(seed)
    # Inverse-CDF draws from the conditional lognormal, not clipping tail draws.
    low = ndtr((np.log(0.1) - mu) / sigma)
    high = ndtr((np.log(cap) - mu) / sigma)
    p = low + rng.random(mu.shape) * (high - low)
    return np.exp(mu + sigma * ndtri(np.clip(p, 1e-12, 1 - 1e-12)))


def diagnostics(idata):
    s = az.summary(idata, var_names=["intercept", "stage_sd", "operator_sd", "sigma", "area_effect", "stage_effect", "operator_effect"])
    result = {"max_rhat": float(az.rhat(idata).to_array().max()), "min_bulk_ess": float(az.ess(idata, method="bulk").to_array().min()),
              "divergences": int(idata.sample_stats.diverging.sum()),
              "chains": int(idata.posterior.sizes["chain"]), "draws_per_chain": int(idata.posterior.sizes["draw"])}
    return result, s


def capacity_outputs(data, imputed):
    observed = data.mw.notna().to_numpy()
    complete = np.where(observed[None, :], data.mw.to_numpy()[None, :], imputed)
    result = data[["id", "name", "status", "county_winner", "matched_county_fips", "operator_group", "mw", "confidence"]].copy()
    result["capacity_basis"] = np.where(observed, "reported", "model estimate")
    for q, label in [(0.05, "p05"), (0.5, "median"), (0.95, "p95")]:
        result[f"capacity_mw_{label}"] = np.quantile(complete, q, axis=0)
    result.to_csv(OUT / "project_capacity_estimates.csv", index=False)
    return complete


def simulate(data, capacity, political="proportional", missing_multiplier=1., time_multiplier=1.,
             county_shared=False, target_multiplier=1., exclude_flagged=False, seed=SEED, retain=False):
    """Same random numbers across scenarios permit direct sensitivity comparisons.

    All times refer to September 15 in each year. No untracked future projects,
    closures, migration, or resource competition are added. All existing records
    inherit their 2024 county winner; county population is fixed at Vintage 2024.
    """
    rng = np.random.default_rng(seed)
    draws, n = capacity.shape
    status = data.status.to_numpy()
    county_code, county_ids = pd.factorize(data.matched_county_fips)
    n_counties = len(county_ids)
    proposed = status == "proposed"
    op = status == "operational"
    cancelled = status == "cancelled"
    under = status == "under_construction"
    permitted = status == "permitted"
    target = capacity.copy()
    target[:, data.mw.isna()] *= missing_multiplier
    target[:, ~op] *= target_multiplier
    q = data.trump_pct.to_numpy() / 100
    if political == "neutral":
        approval = np.full(n, 0.5)
    elif political == "proportional":
        approval = q
    elif political == "winner_step":
        approval = np.where(data.county_winner == "Trump", 0.75, 0.25)
    else:
        raise ValueError(political)
    # These beta distributions encode assumptions, not estimates from stage counts.
    followthrough = rng.beta(8, 2, size=(draws, 1))  # proposed: 80% after assumed approval
    p_permitted = rng.beta(16, 4, size=(draws, 1))   # 80% eventual realization
    p_under = rng.beta(19, 1, size=(draws, 1))       # 95% eventual realization
    u_project = rng.random((draws, n))
    u_county = rng.random((draws, n_counties))[:, county_code]
    approval_draw = (u_county if county_shared else u_project) < approval[None, :]
    follow_draw = rng.random((draws, n)) < followthrough
    built = np.ones((draws, n), dtype=bool)
    built[:, proposed] = (approval_draw & follow_draw)[:, proposed]
    built[:, permitted] = (u_project < p_permitted)[:, permitted]
    built[:, under] = (u_project < p_under)[:, under]
    built[:, cancelled] = False
    if exclude_flagged:
        # Source confidence and unresolved geography are a separate stress test.
        flagged = set(r["id"] for r in json.loads((OUT / "geography_review.json").read_text()))
        flagged.add("stak-energy-north-slope-ak")
        built[:, data.id.isin(flagged).to_numpy() | data.confidence.eq("rumored").to_numpy()] = False
    # First operation: median 4/3/2 years, log SD .45, plus a shared schedule shock.
    medians = np.select([proposed, permitted, under], [4., 3., 2.], default=1.)
    common_delay = rng.lognormal(0, .2, size=(draws, 1))
    first_operation = rng.lognormal(np.log(medians), .45, size=(draws, n)) * common_delay * time_multiplier
    first_operation[:, op] = 0
    # Larger target campuses take longer to fill out: 3 years at 500 MW,
    # sqrt(size) scaling bounded to 1–10 years; additional log SD .35.
    ramp_median = np.clip(3 * np.sqrt(target / 500), 1, 10)
    ramp_years = rng.lognormal(np.log(ramp_median), .35) * common_delay * time_multiplier
    initial_operating_fraction = rng.beta(8, 2, size=(draws, n))
    # One phase opens at 10–30% of target; remaining capacity ramps linearly.
    first_phase = rng.uniform(.1, .3, size=(draws, n))
    county_rows = data.drop_duplicates("matched_county_fips").set_index("matched_county_fips").loc[county_ids]
    county_population = county_rows.population_2024.to_numpy(dtype=float)
    county_party = county_rows.county_winner.to_numpy()
    valid_pop = np.isfinite(county_population)
    active_county = np.zeros(n_counties, dtype=bool)
    active_county[np.unique(county_code[~cancelled])] = True
    membership = np.eye(n_counties)[county_code]
    result, retained = [], {}
    for year in YEARS:
        elapsed = year - 2026
        is_open = built & (elapsed >= first_operation)
        progress = np.clip((elapsed - first_operation) / ramp_years, 0, 1)
        fraction = first_phase + (1 - first_phase) * progress
        fraction[:, op] = initial_operating_fraction[:, op] + (1 - initial_operating_fraction[:, op]) * np.clip(elapsed / ramp_years[:, op], 0, 1)
        operating_mw = np.where(is_open, target * fraction, 0.)
        county_mw = operating_mw @ membership
        if retain:
            retained[year] = operating_mw
        party_values = {}
        for winner in PARTIES:
            project_mask = data.county_winner.eq(winner).to_numpy()
            county_mask = (county_party == winner) & valid_pop
            fixed_population = county_population[county_mask & active_county].sum()
            pop_matched_mw = county_mw[:, county_mask].sum(axis=1)
            residents = ((county_mw[:, county_mask] > 0) * county_population[county_mask]).sum(axis=1)
            intensity = pop_matched_mw / fixed_population * 1000
            host_intensity = pop_matched_mw / residents * 1000
            gw = operating_mw[:, project_mask].sum(axis=1) / 1000
            proposed_mask = project_mask & proposed
            measures = {"operating_gw": gw, "mw_per_1000_fixed_host_population": intensity,
                        "mw_per_1000_operating_host_population": host_intensity,
                        "operating_host_residents_millions": residents / 1e6,
                        "operating_project_count": is_open[:, project_mask].sum(axis=1),
                        "operating_gw_per_listed_proposal": operating_mw[:, proposed_mask].sum(axis=1) / 1000 / proposed_mask.sum()}
            party_values[winner] = measures
            for measure, values in measures.items():
                lo, med, hi = np.quantile(values, [.05, .5, .95])
                result.append({"political": political, "missing_multiplier": missing_multiplier,
                               "time_multiplier": time_multiplier, "target_multiplier": target_multiplier,
                               "county_shared": county_shared, "exclude_flagged": exclude_flagged, "year": year, "winner": winner, "measure": measure,
                               "p05": lo, "median": med, "p95": hi, "fixed_population": fixed_population})
        ratios = party_values["Trump"]["mw_per_1000_fixed_host_population"] / party_values["Harris"]["mw_per_1000_fixed_host_population"]
        lo, med, hi = np.quantile(ratios, [.05, .5, .95])
        result.append({"political": political, "missing_multiplier": missing_multiplier, "time_multiplier": time_multiplier,
                       "target_multiplier": target_multiplier, "county_shared": county_shared, "exclude_flagged": exclude_flagged, "year": year,
                       "winner": "Trump/Harris", "measure": "intensity_ratio", "p05": lo, "median": med, "p95": hi,
                       "fixed_population": None})
    return pd.DataFrame(result), retained


def save_plots(results, data, holdout):
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titlesize": 13, "figure.facecolor": "white"})
    base = results[(results.political == "proportional") & (results.missing_multiplier == 1) &
                   (results.time_multiplier == 1) & (results.target_multiplier == 1) & ~results.county_shared & ~results.exclude_flagged]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    for ax, measure, title, unit in zip(axes,
            ["operating_gw", "mw_per_1000_fixed_host_population"],
            ["Modelled operating capacity", "Modelled capacity per county resident"],
            ["GW", "MW per 1,000 residents"]):
        for winner in PARTIES:
            rows = base[(base.measure == measure) & (base.winner == winner)].sort_values("year")
            ax.plot(rows.year, rows["median"], marker="o" if winner == "Trump" else "s", color=COLORS[winner], label=f"{winner}-won counties")
            ax.fill_between(rows.year, rows.p05, rows.p95, color=COLORS[winner], alpha=.15)
        ax.set(title=title, ylabel=unit, xticks=YEARS, ylim=(0, None))
        ax.grid(axis="y", alpha=.2)
        ax.axvline(2030, color="#666666", linestyle=":", linewidth=1)
    axes[0].legend(frameon=False)
    fig.suptitle("Tracked pipeline, 2026–2036 · proportional-approval scenario", fontsize=15)
    fig.supxlabel("Median and 90% simulation intervals conditional on assumptions; fixed 2024 host-county population", fontsize=10)
    fig.savefig(OUT / "pipeline_timeline.png", dpi=170)
    plt.close(fig)
    rows = results[(results.year == 2030) & (results.measure == "intensity_ratio")].copy()
    labels = []
    for r in rows.itertuples():
        if r.political != "proportional": label = {"neutral": "No political effect", "winner_step": "Winner step: 75% / 25%"}[r.political]
        elif r.missing_multiplier != 1: label = f"Missing sizes × {r.missing_multiplier:g}"
        elif r.time_multiplier != 1: label = f"Construction times × {r.time_multiplier:g}"
        elif r.target_multiplier != 1: label = f"Pipeline targets × {r.target_multiplier:g}"
        elif r.county_shared: label = "Shared county approval outcome"
        elif r.exclude_flagged: label = "Exclude uncertain locations / rumours"
        else: label = "Proportional approval (base)"
        labels.append(label)
    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    positions = np.arange(len(rows))
    ax.errorbar(rows["median"], positions, xerr=[rows["median"]-rows.p05, rows.p95-rows["median"]], fmt="o", color="#334155", capsize=4)
    ax.set(yticks=positions, yticklabels=labels, xlabel="Trump-won / Harris-won capacity per resident", xlim=(0, None),
           title="2030: sensitivity to model assumptions")
    ax.axvline(1, color="#777777", linestyle=":")
    ax.invert_yaxis()
    fig.supxlabel("Points: medians · bars: 90% simulation intervals · same tracked projects in every scenario", fontsize=10)
    fig.savefig(OUT / "scenario_sensitivity.png", dpi=170)
    plt.close(fig)
    counts = data.groupby(["status", "county_winner"]).mw.agg(["size", "count"]).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    pos = np.arange(len(STAGES))
    for i, winner in enumerate(PARTIES):
        subset = counts[counts.county_winner == winner].set_index("status").reindex(STAGES)
        axes[0].barh(pos + (i-.5)*.35, 100*subset["count"]/subset["size"], height=.32, color=COLORS[winner], label=winner)
    axes[0].set(yticks=pos, yticklabels=[s.replace("_", " ") for s in STAGES], xlim=(0, 100), xlabel="Projects with reported MW (%)", title="Reporting coverage by stage and winner")
    axes[0].legend(frameon=False)
    axes[1].errorbar(holdout.actual_mw, holdout["median"], yerr=[holdout["median"]-holdout.p05, holdout.p95-holdout["median"]], fmt="o", alpha=.55, color="#334155", markersize=4)
    axes[1].plot([.1, 10000], [.1, 10000], linestyle=":", color="#777777")
    axes[1].set(xscale="log", yscale="log", xlabel="Withheld reported MW", ylabel="Predicted MW (90% interval)", title="Capacity model: held-out projects")
    fig.savefig(OUT / "model_validation.png", dpi=170)
    plt.close(fig)


def run(draws=1000, tune=2000, refit=False):
    OUT.mkdir(exist_ok=True)
    data, groups = load_data()
    observed = data.mw.notna().to_numpy()
    rng = np.random.default_rng(SEED)
    holdout_mask = np.zeros(len(data), dtype=bool)
    for stage in STAGES:
        indices = np.flatnonzero(observed & data.status.eq(stage).to_numpy())
        holdout_mask[rng.choice(indices, max(1, round(.2 * len(indices))), replace=False)] = True
    diagnostic_reports = {}
    for label, mask in [("holdout", observed & ~holdout_mask), ("full", observed)]:
        path = OUT / f"capacity_{label}_posterior.nc"
        signature = hashlib.sha256((data.loc[mask, ["id", "mw", "acres", "stage_idx", "operator_idx"]].to_json() +
                                   json.dumps([groups, STAGES, draws, tune, SEED, "lognormal-v2-acreage-targetaccept995"])).encode()).hexdigest()
        manifest_path = OUT / f"capacity_{label}_manifest.json"
        cached = path.exists() and manifest_path.exists() and json.loads(manifest_path.read_text()).get("signature") == signature and not refit
        idata = az.from_netcdf(path) if cached else fit_capacity(data, groups, mask, draws, tune, SEED)
        if not cached:
            idata.to_netcdf(path)
            write_json(manifest_path, {"signature": signature, "pymc_version": pm.__version__, "seed": SEED})
        diag, table = diagnostics(idata)
        diagnostic_reports[label] = diag
        table.to_csv(OUT / f"capacity_{label}_diagnostics.csv")
        print(label, diag, flush=True)
        if diag["max_rhat"] > 1.01 or diag["divergences"] or diag["min_bulk_ess"] < 400:
            raise RuntimeError(f"Sampler needs review: {diag}")
        prediction = predict_capacity(idata, data)
        if label == "holdout":
            lo, med, hi = np.quantile(prediction[:, holdout_mask], [.05, .5, .95], axis=0)
            actual = data.loc[holdout_mask, "mw"].to_numpy()
            held = pd.DataFrame({"id": data.loc[holdout_mask, "id"], "status": data.loc[holdout_mask, "status"],
                                 "actual_mw": actual, "p05": lo, "median": med, "p95": hi})
            held.to_csv(OUT / "capacity_holdout_predictions.csv", index=False)
            diagnostic_reports["holdout_prediction"] = {"n": len(actual), "coverage_90": float(np.mean((actual >= lo) & (actual <= hi))),
                "median_absolute_log_error": float(np.median(np.abs(np.log(actual/med)))),
                "median_multiplicative_error": float(np.exp(np.median(np.abs(np.log(actual/med))))),
                "actual_total_gw": float(actual.sum()/1000),
                "predicted_total_gw_p05_median_p95": (np.quantile(prediction[:, holdout_mask].sum(axis=1), [.05,.5,.95])/1000).tolist()}
            # Baseline estimator fitted only on the training portion.
            baseline = data.loc[observed & ~holdout_mask].groupby("status").mw.median()
            baseline_values = data.loc[holdout_mask, "status"].map(baseline).to_numpy()
            diagnostic_reports["holdout_prediction"]["stage_median_baseline_multiplicative_error"] = float(np.exp(np.median(np.abs(np.log(actual/baseline_values)))))
        else:
            complete = capacity_outputs(data, prediction)
    write_json(OUT / "model_diagnostics.json", diagnostic_reports)
    scenarios = [{"political": p} for p in ["neutral", "proportional", "winner_step"]]
    scenarios += [{"missing_multiplier": m} for m in [.5, 2.]]
    scenarios += [{"time_multiplier": m} for m in [.75, 1.5]]
    scenarios += [{"target_multiplier": .5}, {"county_shared": True}, {"exclude_flagged": True}]
    all_results = []
    for config in scenarios:
        result, _ = simulate(data, complete, **config)
        all_results.append(result)
    results = pd.concat(all_results, ignore_index=True)
    results.to_csv(OUT / "pipeline_scenarios.csv", index=False)
    # Project-level 2030 operating-capacity draws retain zeros for projects not built.
    _, raw = simulate(data, complete, retain=True)
    per_project = data[["id", "name", "county_winner", "status"]].copy()
    for q, label in [(.05, "p05"), (.5, "median"), (.95, "p95")]:
        per_project[f"operating_mw_2030_{label}"] = np.quantile(raw[2030], q, axis=0)
    per_project["mean_operating_mw_2030"] = raw[2030].mean(axis=0)
    per_project["probability_operating_2030"] = (raw[2030] > 0).mean(axis=0)
    per_project.to_csv(OUT / "project_operating_2030.csv", index=False)
    # Non-closing trajectories, probabilities, known sizes, county totals, and bounds.
    assert np.array_equal(complete[:, observed], np.broadcast_to(data.mw.to_numpy()[observed], complete[:, observed].shape))
    assert np.all(np.isfinite(complete)) and (complete > 0).all()
    assert (raw[2026][:, data.status.ne("operational")] == 0).all()
    assert all((raw[y][:, data.status.eq("cancelled")] == 0).all() for y in YEARS)
    assert all((raw[b] >= raw[a] - 1e-9).all() for a, b in zip(YEARS, YEARS[1:]))
    assert results[["p05", "median", "p95"]].notna().all().all()
    assert (results.p05 <= results["median"]).all() and (results["median"] <= results.p95).all()
    proposed = data.status.eq("proposed").to_numpy()
    summary = {"years": YEARS, "as_of": "2026-09-15", "seed": SEED, "draws": complete.shape[0],
               "reported_projects": int(observed.sum()), "imputed_projects": int((~observed).sum()),
               "unknown_total_gw_p05_median_p95": (np.quantile(complete[:, ~observed].sum(axis=1), [.05,.5,.95])/1000).tolist(),
               "proposed_target_gw_per_location_p05_median_p95": (np.quantile(complete[:, proposed].mean(axis=1), [.05,.5,.95])/1000).tolist(),
               "checks": "Passed: original MW retained; positive finite draws; operational-only baseline; cancelled=0; nondecreasing trajectories; ordered intervals",
               "exclusions": {"population_unmatched_projects": data.loc[data.population_2024.isna(), "id"].tolist()},
               "assumptions": {"capacity_model": "lognormal with partial pooling by stage and operator plus standardized log-acreage; unknown acreage integrated as N(0,1); conditional missing-MW range 0.1–10000; no political size predictor",
                 "proposed_approval": "neutral=0.5; proportional=Trump vote share of all ballots; winner_step=0.75/0.25",
                 "post_approval_realization": "Beta(8,2), mean 0.8, shared per simulation",
                 "permitted_realization": "Beta(16,4), mean 0.8, shared per simulation",
                 "construction_realization": "Beta(19,1), mean 0.95, shared per simulation",
                 "time_to_operation_median_years": {"proposed": 4, "permitted": 3, "under_construction": 2},
                 "time_uncertainty": "log SD 0.45 per project; common lognormal shock with log SD 0.2",
                 "ramp": "median clip(3*sqrt(target MW/500),1,10) years; log SD .35 and shared schedule shock",
                 "first_phase": "Uniform(0.1,0.3) fraction of target at opening",
                 "operational_baseline": "Beta(8,2) fraction of reported/imputed target; remaining capacity ramps; baseline is also modelled",
                 "resident_accounting": "All county residents receive county operating MW / county population; county residents counted once",
                 "intensity_denominator": "Fixed union of non-cancelled tracked host counties with 2024 population; also report dynamic operating-host denominator",
                 "structural": "Fixed pipeline and county winners; no new announcements, closures, population growth, grid constraint or demand cap",
                 "intervals": "90% simulation intervals conditional on scenario; not calibrated forecast coverage"}}
    write_json(OUT / "model_summary.json", summary)
    save_plots(results, data, held)
    print(json.dumps(diagnostic_reports, indent=2), flush=True)
    print(results[(results.year == 2030) & results.measure.isin(["operating_gw", "intensity_ratio"])].to_string(index=False), flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--tune", type=int, default=2000)
    parser.add_argument("--refit", action="store_true")
    args = parser.parse_args()
    run(args.draws, args.tune, args.refit)
