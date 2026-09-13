// Filtering logic
function applyFilters() {
  const query = document
    .getElementById("search-input")
    .value.toLowerCase()
    .trim();
  const winner = document.getElementById("winner-filter").value;
  const status = document.getElementById("status-filter").value;
  const tier = document.getElementById("tier-filter").value;
  const operator = document.getElementById("operator-filter").value;

  filteredData = facilities.filter((f) => {
    // Search query
    if (query) {
      const matchText = [
        f.name,
        f.operator,
        f.city,
        f.matched_county_name,
        f.state,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!matchText.includes(query)) return false;
    }

    // Winner
    if (winner !== "all" && f.county_winner !== winner) return false;

    // Status
    if (status !== "all" && f.status !== status) return false;

    // Tier
    if (tier !== "all") {
      if (politicalTier(f) !== tier) return false;
    }

    // Operator
    if (operator !== "all") {
      const op = (f.operator || "").toLowerCase();
      if (operator === "google" && !op.includes("google")) return false;
      if (
        operator === "amazon" &&
        !(op.includes("amazon") || op.includes("aws"))
      )
        return false;
      if (
        operator === "meta" &&
        !(op.includes("meta") || op.includes("facebook"))
      )
        return false;
      if (operator === "microsoft" && !op.includes("microsoft")) return false;
      if (operator === "qts" && !op.includes("qts")) return false;
      if (operator === "vantage" && !op.includes("vantage")) return false;
      if (operator === "xai" && !(op.includes("xai") || op.includes("elon")))
        return false;
    }

    return true;
  });

  currentPage = 1;
  document.getElementById("table-search").value =
    document.getElementById("search-input").value;
  sortData();
  renderMapMarkers();
  renderSummary();
  initCharts();
  document.getElementById("map-empty").hidden = filteredData.length > 0;
  document.getElementById("btn-export-csv").disabled =
    filteredData.length === 0;
}
// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  applyFilters();

  // Filters
  document
    .getElementById("search-input")
    .addEventListener("input", applyFilters);
  document
    .getElementById("winner-filter")
    .addEventListener("change", applyFilters);
  document
    .getElementById("status-filter")
    .addEventListener("change", applyFilters);
  document
    .getElementById("tier-filter")
    .addEventListener("change", applyFilters);
  document
    .getElementById("operator-filter")
    .addEventListener("change", applyFilters);
  document
    .getElementById("size-toggle")
    .addEventListener("change", renderMapMarkers);

  // Table search sync
  document.getElementById("table-search").addEventListener("input", (e) => {
    document.getElementById("search-input").value = e.target.value;
    applyFilters();
  });

  // Reset
  document.getElementById("btn-reset-filters").addEventListener("click", () => {
    document.getElementById("search-input").value = "";
    document.getElementById("table-search").value = "";
    document.getElementById("winner-filter").value = "all";
    document.getElementById("status-filter").value = "all";
    document.getElementById("tier-filter").value = "all";
    document.getElementById("operator-filter").value = "all";
    document.getElementById("size-toggle").value = "scaled";
    applyFilters();
  });

  // Pagination
  document.getElementById("btn-prev-page").addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderTable();
    }
  });
  document.getElementById("btn-next-page").addEventListener("click", () => {
    const totalPages = Math.ceil(filteredData.length / pageSize);
    if (currentPage < totalPages) {
      currentPage++;
      renderTable();
    }
  });

  // Sorting
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.tabIndex = 0;
    th.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        sortData(th.getAttribute("data-sort"));
      }
    });
    th.addEventListener("click", () => {
      sortData(th.getAttribute("data-sort"));
    });
  });

  // Export CSV
  document
    .getElementById("btn-export-csv")
    .addEventListener("click", exportFilteredCSV);
});
