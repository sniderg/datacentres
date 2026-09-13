// Charts Initialization
function initCharts() {
  [chartStatus, chartCapacity, chartStates, chartOperators].forEach(
    (c) => c && c.destroy(),
  );
  // 1. Status Chart
  const statusLabels = [
    "Operational",
    ["Under", "construction"],
    "Permitted",
    "Proposed",
    "Cancelled",
  ];
  const statusKeys = [
    "operational",
    "under_construction",
    "permitted",
    "proposed",
    "cancelled",
  ];

  const statusTrump = statusKeys.map(
    (k) =>
      filteredData.filter((f) => f.status === k && f.county_winner === "Trump")
        .length,
  );
  const statusHarris = statusKeys.map(
    (k) =>
      filteredData.filter((f) => f.status === k && f.county_winner === "Harris")
        .length,
  );

  const ctxStatus = document.getElementById("chart-status").getContext("2d");
  chartStatus = new Chart(ctxStatus, {
    type: "bar",
    data: {
      labels: statusLabels,
      datasets: [
        {
          label: "Trump Counties",
          data: statusTrump,
          backgroundColor: "#dc2626",
          borderRadius: 4,
        },
        {
          label: "Harris Counties",
          data: statusHarris,
          backgroundColor: "#2563eb",
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, beginAtZero: true, grid: { color: "#e2e8f0" } },
      },
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 12, font: { family: "Inter" } },
        },
      },
    },
  });

  // 2. Capacity by Political Tier Chart
  const tierLabels = [
    "Strong Trump",
    "Lean Trump",
    "Lean Harris",
    "Strong Harris",
  ];
  const tierMW = [
    "strong-trump",
    "lean-trump",
    "lean-harris",
    "strong-harris",
  ].map((t) =>
    sum(
      filteredData.filter((f) => politicalTier(f) === t),
      "mw",
    ),
  );

  const ctxCapacity = document
    .getElementById("chart-capacity")
    .getContext("2d");
  chartCapacity = new Chart(ctxCapacity, {
    type: "doughnut",
    data: {
      labels: tierLabels,
      datasets: [
        {
          data: tierMW,
          backgroundColor: ["#b91c1c", "#ef4444", "#3b82f6", "#1d4ed8"],
          borderWidth: 2,
          borderColor: "#ffffff",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 10,
            padding: 16,
            font: { family: "Inter", size: 12 },
          },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const val = ctx.raw || 0;
              const total = tierMW.reduce((a, b) => a + b, 0);
              const pct = (total ? (val / total) * 100 : 0).toFixed(1);
              return ` ${ctx.label}: ${fmtNum(Math.round(val))} MW (${pct}%)`;
            },
          },
        },
      },
    },
  });

  // 3. Top States Chart
  const topStates = [...new Set(filteredData.map((f) => f.state))]
    .sort(
      (a, b) =>
        filteredData.filter((f) => f.state === b).length -
          filteredData.filter((f) => f.state === a).length ||
        a.localeCompare(b),
    )
    .slice(0, 10);
  const stateTrump = topStates.map(
    (st) =>
      filteredData.filter((f) => f.state === st && f.county_winner === "Trump")
        .length,
  );
  const stateHarris = topStates.map(
    (st) =>
      filteredData.filter((f) => f.state === st && f.county_winner === "Harris")
        .length,
  );

  const ctxStates = document.getElementById("chart-states").getContext("2d");
  chartStates = new Chart(ctxStates, {
    type: "bar",
    data: {
      labels: topStates,
      datasets: [
        {
          label: "Trump Counties",
          data: stateTrump,
          backgroundColor: "#dc2626",
          borderRadius: 4,
        },
        {
          label: "Harris Counties",
          data: stateHarris,
          backgroundColor: "#2563eb",
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, beginAtZero: true, grid: { color: "#e2e8f0" } },
      },
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 12, font: { family: "Inter" } },
        },
      },
    },
  });

  // 4. Operators Chart
  const ops = [
    {
      label: "Google",
      filter: (f) => (f.operator || "").toLowerCase().includes("google"),
    },
    {
      label: "Amazon / AWS",
      filter: (f) => {
        const o = (f.operator || "").toLowerCase();
        return o.includes("amazon") || o.includes("aws");
      },
    },
    {
      label: "Meta",
      filter: (f) => {
        const o = (f.operator || "").toLowerCase();
        return o.includes("meta") || o.includes("facebook");
      },
    },
    {
      label: "Microsoft",
      filter: (f) => (f.operator || "").toLowerCase().includes("microsoft"),
    },
    {
      label: "QTS",
      filter: (f) => (f.operator || "").toLowerCase().includes("qts"),
    },
    {
      label: "Vantage",
      filter: (f) => (f.operator || "").toLowerCase().includes("vantage"),
    },
  ];

  const opLabels = ops.map((o) => o.label);
  const opTrump = ops.map(
    (o) =>
      filteredData.filter((f) => o.filter(f) && f.county_winner === "Trump")
        .length,
  );
  const opHarris = ops.map(
    (o) =>
      filteredData.filter((f) => o.filter(f) && f.county_winner === "Harris")
        .length,
  );

  const ctxOperators = document
    .getElementById("chart-operators")
    .getContext("2d");
  chartOperators = new Chart(ctxOperators, {
    type: "bar",
    data: {
      labels: opLabels,
      datasets: [
        {
          label: "Trump Counties",
          data: opTrump,
          backgroundColor: "#dc2626",
          borderRadius: 4,
        },
        {
          label: "Harris Counties",
          data: opHarris,
          backgroundColor: "#2563eb",
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      scales: {
        x: { stacked: true, beginAtZero: true, grid: { color: "#e2e8f0" } },
        y: { stacked: true, grid: { display: false } },
      },
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 12, font: { family: "Inter" } },
        },
      },
    },
  });
}
