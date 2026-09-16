const sum = (rows, key) => rows.reduce((s, r) => s + (Number(r[key]) || 0), 0);
const politicalTier = (f) =>
  f.county_winner === "Trump"
    ? f.trump_pct >= 65
      ? "strong-trump"
      : "lean-trump"
    : f.harris_pct >= 65
      ? "strong-harris"
      : "lean-harris";
const pct = (a, b) => (b ? ((100 * a) / b).toFixed(1) + "%" : "—");
const split = (t, h) =>
  `<div class="kpi-split-bar"><div class="kpi-split-trump" style="width:${t || 0}%"></div><div class="kpi-split-harris" style="width:${h || 0}%"></div></div>`;
const metric = (title, value, note, t, h) =>
  `<div class="kpi-card"><div class="kpi-title">${title}</div><div class="kpi-value">${value}</div>${t != null ? split(t, h) : ""}<div class="metric-note">${note}</div></div>`;
function calculateSummary(rows) {
  const counties = [
    ...new Map(rows.map((f) => [f.matched_county_fips, f])).values(),
  ];
  const mwRows = rows.filter((f) => f.mw != null);
  const popCounties = counties.filter((f) => f.population_2024 != null);
  const covered = mwRows.filter((f) => f.population_2024 != null);
  const capacityCounties = [
    ...new Map(covered.map((f) => [f.matched_county_fips, f])).values(),
  ];
  const mw = sum(mwRows, "mw");
  return {
    counties,
    mwRows,
    popCounties,
    covered,
    capacityCounties,
    mw,
    population: sum(popCounties, "population_2024"),
  };
}
function renderSummary() {
  const r = filteredData,
    s = calculateSummary(r),
    red = r.filter((f) => f.county_winner === "Trump");
  const tMW = sum(red, "mw"),
    inv = sum(r, "investment"),
    ti = sum(red, "investment");
  document.getElementById("summary-cards").innerHTML =
    metric(
      "Selected projects",
      fmtNum(r.length),
      `${red.length} Trump-won · ${r.length - red.length} Harris-won`,
      r.length ? (100 * red.length) / r.length : 0,
      r.length ? (100 * (r.length - red.length)) / r.length : 0,
    ) +
    metric(
      "Reported capacity",
      s.mwRows.length ? `${fmtNum(Math.round(s.mw))} <small>MW</small>` : "—",
      `${pct(tMW, s.mw)} in Trump-won counties`,
      s.mw ? (100 * tMW) / s.mw : 0,
      s.mw ? (100 * (s.mw - tMW)) / s.mw : 0,
    ) +
    metric(
      "Reported investment",
      r.some((f) => f.investment != null) ? fmtMoney(inv) : "—",
      `${pct(ti, inv)} in Trump-won counties`,
      inv ? (100 * ti) / inv : 0,
      inv ? (100 * (inv - ti)) / inv : 0,
    ) +
    metric(
      "Host counties",
      fmtNum(s.counties.length),
      `${s.popCounties.length} with matching population`,
    ) +
    metric(
      "Host-county residents",
      s.popCounties.length
        ? `${(s.population / 1e6).toFixed(2)}<small>M</small>`
        : "—",
      "2024 Census estimate · unique counties",
    );
  document.getElementById("coverage-note").textContent =
    `Selected scope: ${r.length} projects · MW reported for ${s.mwRows.length}/${r.length} · investment reported for ${r.filter((f) => f.investment != null).length}/${r.length} · population matched for ${s.popCounties.length}/${s.counties.length} counties. All stages includes cancelled projects. Red = Trump-won; blue = Harris-won.`;
  const weighted = (rows, weight) => {
    const denominator = rows.reduce((a, f) => a + weight(f), 0);
    return ["trump_pct", "harris_pct"].map((k) =>
      denominator
        ? rows.reduce((a, f) => a + weight(f) * f[k], 0) / denominator
        : null,
    );
  };
  const card = (title, values, note) =>
    `<div class="weighting-card"><h3>${title}</h3><div class="weighting-numbers"><span class="weighting-stat-large trump">${values[0] == null ? "—" : values[0].toFixed(1) + "%"}</span><span class="weighting-stat-large harris">${values[1] == null ? "—" : values[1].toFixed(1) + "%"}</span></div>${split(...values)}<div class="metric-note">Trump / Harris · gray = other votes</div><p>${note}</p></div>`;
  const voteTotal = sum(s.counties, "total_votes");
  document.getElementById("weighting-cards").innerHTML =
    card(
      "Capacity-weighted vote share",
      weighted(s.mwRows, (f) => f.mw),
      "Each reported MW weights its county’s vote share. Includes only the selected stages; capacity is not actual electricity consumption.",
    ) +
    card(
      "Votes cast in host counties",
      voteTotal
        ? [
            (100 * sum(s.counties, "trump_votes")) / voteTotal,
            (100 * sum(s.counties, "harris_votes")) / voteTotal,
          ]
        : [null, null],
      `${fmtNum(voteTotal)} presidential votes, with each host county counted once. This measures participating voters.`,
    ) +
    card(
      "Population-weighted vote share",
      weighted(s.popCounties, (f) => f.population_2024),
      "Each resident weights their county’s observed vote share. A geographic index, not an estimate of residents’ preferences or turnout-adjusted votes.",
    ) +
    card(
      "Capacity × population index",
      weighted(s.covered, (f) => f.mw * f.population_2024),
      "Exploratory weighting by reported MW × county residents. This intentionally gives more weight to large projects in populous counties; no causal or burden interpretation.",
    );
}
