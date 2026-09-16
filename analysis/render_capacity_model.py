"""Render the capacity hierarchy with LaTeX math and noncrossing connectors.

Run with MPLCONFIGDIR=/tmp/datacentres-mpl python analysis/render_capacity_model.py.
Math is embedded as vector paths, so the site needs no external math renderer.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({'font.family': 'DejaVu Sans', 'mathtext.fontset': 'stix',
                     'svg.fonttype': 'path', 'svg.hashsalt': 'capacity-model'})
fig, ax = plt.subplots(figsize=(10, 9.4))
fig.patch.set_facecolor('white')
ax.set(xlim=(0, 10), ylim=(0, 9.4))
ax.axis('off')
fig.subplots_adjust(0, 0, 1, 1)
ink, muted, blue = '#172b46', '#52657b', '#346c9c'

def card(x, y, w, h, title, lines, accent=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
        boxstyle='round,pad=0.02,rounding_size=0.14', linewidth=1,
        edgecolor='#b9cfe1' if accent else '#dce4ed',
        facecolor='#edf5fb' if accent else '#f8fafc', zorder=2))
    ax.text(x+w/2, y+h-0.31, title, ha='center', va='center',
            fontsize=12, weight='bold', color=blue if accent else ink)
    for j, line in enumerate(lines):
        ax.text(x+w/2, y+h-0.72-j*0.36, line, ha='center', va='center',
                fontsize=16, color=ink)

def arrow(points):
    from matplotlib.path import Path as MPath
    path = MPath(points, [MPath.MOVETO]+[MPath.LINETO]*(len(points)-1))
    ax.add_patch(FancyArrowPatch(path=path, arrowstyle='-|>',
        mutation_scale=12, linewidth=1.4, color='#8ba2b8', zorder=1))

ax.text(0.5, 8.99, 'PROJECT CAPACITY MODEL', fontsize=11, weight='bold', color=blue)
ax.text(0.5, 8.61, 'Priors → shared model → capacity estimates', fontsize=15, color=ink)
card(0.5, 6.5, 4.25, 1.65, 'Stage · partial pooling', [
    r'$z_s \sim \mathcal{N}(0,\,1),\quad \tau_s \sim \mathrm{HalfNormal}(1)$',
    r'$a_s = \tau_s z_s$'])
card(5.25, 6.5, 4.25, 1.65, 'Operator · partial pooling', [
    r'$z_o \sim \mathcal{N}(0,\,1),\quad \tau_o \sim \mathrm{HalfNormal}(1)$',
    r'$b_o = \tau_o z_o$'])
card(0.5, 4.75, 4.25, 1.3, 'Baseline capacity', [
    r'$\alpha \sim \mathcal{N}(\log 300,\,2)$'])
card(5.25, 4.75, 4.25, 1.3, 'Standardized log-acreage', [
    r'$\beta \sim \mathcal{N}(0.7,\,0.7)$'])
# Outer lanes carry the group effects past the baseline/acreage cards.
arrow([(0.5,7.3),(0.22,7.3),(0.22,3.82),(0.9,3.82)])
arrow([(9.5,7.3),(9.78,7.3),(9.78,3.82),(9.1,3.82)])
arrow([(2.625,4.75),(2.625,4.25)])
arrow([(7.375,4.75),(7.375,4.25)])
card(0.9, 2.45, 8.2, 1.8, 'Shared log-capacity model', [
    r'$\mu_i = \alpha + a_{s[i]} + b_{o[i]} + \beta x_i$',
    r'$\sigma \sim \mathrm{HalfNormal}(1.5)$',
    r'$\log(\mathrm{MW}_i) \sim \mathcal{N}(\mu_i,\,\sigma_{i,\mathrm{eff}})$'], True)
arrow([(2.625,2.45),(2.625,1.9)])
arrow([(7.375,2.45),(7.375,1.9)])
card(0.5, 0.65, 4.25, 1.25, 'Reported projects', [r'$\mathrm{Observed\ MW\ informs\ the\ fit}$'])
card(5.25, 0.65, 4.25, 1.25, 'Missing project sizes', [r'$\mathrm{Posterior\ predictive\ MW}$'])
ax.text(7.375, 0.84, 'Conditioned to 0.1–10,000 MW', ha='center', fontsize=10, color=muted)
ax.text(0.5, 0.26, r'Normal priors use (mean, SD). Unknown acreage: $\sigma_{i,\mathrm{eff}}=\sqrt{\sigma^2+\beta^2}$; otherwise $\sigma_{i,\mathrm{eff}}=\sigma$.', fontsize=10, color=muted)
fig.savefig(Path(__file__).with_name('capacity_model.svg'), metadata={
    'Date': None,
    'Title': 'Hierarchical project capacity model',
    'Description': 'Stage and operator priors, baseline and acreage feed a shared log-capacity model, branching to reported and missing project sizes.'})
plt.close(fig)

output = Path(__file__).with_name('capacity_model.svg')
output.write_text('\n'.join(line.rstrip() for line in output.read_text().splitlines()) + '\n')
