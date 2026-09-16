(() => {
  const model = window.PIPELINE_MODEL;
  if (!model) return;

  const scenarioLabels = {
    proportional: "approval proportional to Trump vote share",
    neutral: "neutral 50% approval",
    winner_step: "winner-take-all county approval (75% / 25%)",
  };
  let capacityChart;
  let intensityChart;

  const metricAt = (scenario, year, winner, measure) =>
    model.scenarios[scenario][String(year)][winner][measure];
  const interval = (metric, digits = 1) =>
    `${metric.p05.toFixed(digits)}–${metric.p95.toFixed(digits)}`;

  function renderKpis(scenario) {
    const year = 2030;
    const trumpGw = metricAt(scenario, year, "Trump", "operating_gw");
    const harrisGw = metricAt(scenario, year, "Harris", "operating_gw");
    const trumpIntensity = metricAt(
      scenario,
      year,
      "Trump",
      "mw_per_1000_fixed_host_population",
    );
    const harrisIntensity = metricAt(
      scenario,
      year,
      "Harris",
      "mw_per_1000_fixed_host_population",
    );
    const ratio = metricAt(scenario, year, "Trump/Harris", "intensity_ratio");
    const trumpCount = metricAt(scenario, year, "Trump", "operating_project_count");
    const harrisCount = metricAt(scenario, year, "Harris", "operating_project_count");

    document.getElementById("outlook-kpis").innerHTML = `
      <article class="outlook-kpi">
        <span class="outlook-kpi-label">Operating GW in 2030</span>
        <div class="outlook-pair"><strong class="trump">${trumpGw.median.toFixed(1)}</strong><strong class="harris">${harrisGw.median.toFixed(1)}</strong></div>
        <span class="outlook-kpi-meta">Trump / Harris · 90% intervals ${interval(trumpGw)} / ${interval(harrisGw)}</span>
      </article>
      <article class="outlook-kpi">
        <span class="outlook-kpi-label">MW per 1,000 residents</span>
        <div class="outlook-pair"><strong class="trump">${trumpIntensity.median.toFixed(2)}</strong><strong class="harris">${harrisIntensity.median.toFixed(2)}</strong></div>
        <span class="outlook-kpi-meta">Trump / Harris · fixed host-county populations</span>
      </article>
      <article class="outlook-kpi spotlight">
        <span class="outlook-kpi-label">Trump-to-Harris intensity ratio</span>
        <div class="outlook-single">${ratio.median.toFixed(2)}<small>×</small></div>
        <span class="outlook-kpi-meta">90% interval ${interval(ratio, 2)} · ${Math.round(trumpCount.median)} / ${Math.round(harrisCount.median)} operating projects</span>
      </article>`;

    document.getElementById("outlook-note").textContent =
      `Scenario: ${scenarioLabels[scenario]}. It covers the 474 currently tracked projects only, uses 2024 county winners and populations, and includes no future announcements, closures, population growth, grid constraint or demand cap.`;
  }

  function bandDatasets(scenario, measure, decimals) {
    const years = model.years;
    const definitions = [
      { winner: "Trump", color: "220, 38, 38" },
      { winner: "Harris", color: "37, 99, 235" },
    ];
    const datasets = [];
    definitions.forEach(({ winner, color }) => {
      const metrics = years.map((year) => metricAt(scenario, year, winner, measure));
      datasets.push(
        {
          label: `${winner} 5th percentile`,
          data: metrics.map((m) => Number(m.p05.toFixed(decimals))),
          borderColor: "transparent",
          backgroundColor: "transparent",
          pointRadius: 0,
          borderWidth: 0,
          tension: 0.25,
          _interval: true,
        },
        {
          label: `${winner} 90% interval`,
          data: metrics.map((m) => Number(m.p95.toFixed(decimals))),
          borderColor: "transparent",
          backgroundColor: `rgba(${color}, 0.13)`,
          pointRadius: 0,
          borderWidth: 0,
          fill: "-1",
          tension: 0.25,
          _interval: true,
        },
        {
          label: winner,
          data: metrics.map((m) => Number(m.median.toFixed(decimals))),
          borderColor: `rgb(${color})`,
          backgroundColor: `rgb(${color})`,
          pointBackgroundColor: "#fff",
          pointBorderWidth: 2,
          pointRadius: 3,
          borderWidth: 3,
          tension: 0.25,
        },
      );
    });
    return datasets;
  }

  function chartOptions(unit) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false } },
        y: {
          beginAtZero: true,
          grid: { color: "#e2e8f0" },
          ticks: { callback: (value) => `${value}${unit}` },
        },
      },
      plugins: {
        legend: {
          position: "top",
          labels: {
            boxWidth: 12,
            font: { family: "Inter" },
            filter: (item, data) => !data.datasets[item.datasetIndex]._interval,
          },
        },
        tooltip: {
          filter: (item) => !item.dataset._interval,
          callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${ctx.raw}${unit}` },
        },
      },
    };
  }

  function renderCharts(scenario) {
    if (capacityChart) capacityChart.destroy();
    if (intensityChart) intensityChart.destroy();
    capacityChart = new Chart(document.getElementById("chart-outlook-capacity"), {
      type: "line",
      data: {
        labels: model.years,
        datasets: bandDatasets(scenario, "operating_gw", 1),
      },
      options: chartOptions(" GW"),
    });
    intensityChart = new Chart(document.getElementById("chart-outlook-intensity"), {
      type: "line",
      data: {
        labels: model.years,
        datasets: bandDatasets(
          scenario,
          "mw_per_1000_fixed_host_population",
          2,
        ),
      },
      options: chartOptions(""),
    });
  }

  function render(scenario) {
    renderKpis(scenario);
    renderCharts(scenario);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("outlook-scenario");
    render(select.value);
    select.addEventListener("change", () => render(select.value));
  });
})();
