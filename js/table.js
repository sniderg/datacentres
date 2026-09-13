// Render Table
function renderTable() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";

  const startIndex = (currentPage - 1) * pageSize;
  const pageItems = filteredData.slice(startIndex, startIndex + pageSize);

  if (pageItems.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:30px; color:#64748b;">No facilities match the active filter criteria.</td></tr>`;
    document.getElementById("table-info").textContent =
      "Showing 0 of 0 facilities";
    document.getElementById("page-num-display").textContent = "0 / 0";
    document.getElementById("btn-prev-page").disabled = true;
    document.getElementById("btn-next-page").disabled = true;
    return;
  }

  pageItems.forEach((f) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="td-wrap" style="font-weight:600; color:#0f172a;">${escapeHtml(f.name || "Data Center")}</td>
      <td>${escapeHtml(f.operator || "—")}</td>
      <td>${escapeHtml([f.matched_county_name, f.state].filter(Boolean).join(", "))}</td>
      <td><span class="badge badge-${f.status || "operational"}">${f.status ? f.status.replace("_", " ") : "—"}</span></td>
      <td style="text-align:right; font-weight:600;">${f.mw ? fmtNum(f.mw) : "—"}</td>
      <td style="text-align:right;">${fmtMoney(f.investment)}</td>
      <td><span class="badge ${f.county_winner === "Trump" ? "badge-trump" : "badge-harris"}">${f.county_winner || "—"}</span></td>
      <td style="text-align:right; font-weight:600;">${fmtPct(f.trump_pct)}</td>
      <td style="text-align:right; color:${f.county_winner === "Trump" ? "var(--trump-dark)" : "var(--harris-dark)"}; font-weight:600;">
        ${f.margin_pct != null ? (f.margin_pct >= 0 ? "+" : "") + f.margin_pct.toFixed(1) + "%" : "—"}
      </td>
    `;

    // Clicking a row flies the map to that facility!
    tr.addEventListener("click", () => {
      if (f.lat != null && f.lon != null) {
        map.flyTo([f.lat, f.lon], 9, { duration: 1.2 });
        // Find marker and open popup
        markersLayer.eachLayer((layer) => {
          const latLng = layer.getLatLng();
          if (
            Math.abs(latLng.lat - f.lat) < 0.0001 &&
            Math.abs(latLng.lng - f.lon) < 0.0001
          ) {
            layer.openPopup();
          }
        });
        window.scrollTo({
          top: document.querySelector(".map-section").offsetTop - 20,
          behavior: "smooth",
        });
      }
    });

    tbody.appendChild(tr);
  });

  const totalPages = Math.ceil(filteredData.length / pageSize) || 1;
  document.getElementById("table-info").textContent =
    `Showing ${startIndex + 1} to ${Math.min(startIndex + pageSize, filteredData.length)} of ${filteredData.length} facilities`;
  document.getElementById("page-num-display").textContent =
    `${currentPage} / ${totalPages}`;
  document.getElementById("btn-prev-page").disabled = currentPage <= 1;
  document.getElementById("btn-next-page").disabled = currentPage >= totalPages;
}

// Sorting logic
function sortData(field) {
  if (field && sortField === field) {
    sortDirection = sortDirection === "asc" ? "desc" : "asc";
  } else {
    if (field) sortField = field;
    if (field)
      sortDirection =
        field === "mw" ||
        field === "investment" ||
        field === "trump_pct" ||
        field === "margin_pct"
          ? "desc"
          : "asc";
  }

  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.classList.remove("sorted-asc", "sorted-desc");
    th.setAttribute("aria-sort", "none");
    if (th.getAttribute("data-sort") === sortField) {
      th.classList.add(sortDirection === "asc" ? "sorted-asc" : "sorted-desc");
      th.setAttribute(
        "aria-sort",
        sortDirection === "asc" ? "ascending" : "descending",
      );
    }
  });

  filteredData.sort((a, b) => {
    let va = a[sortField];
    let vb = b[sortField];

    if (sortField === "location") {
      va = (a.state || "") + (a.matched_county_name || "");
      vb = (b.state || "") + (b.matched_county_name || "");
    }

    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;

    if (typeof va === "string") {
      return sortDirection === "asc"
        ? va.localeCompare(vb)
        : vb.localeCompare(va);
    }
    return sortDirection === "asc" ? va - vb : vb - va;
  });

  currentPage = 1;
  renderTable();
}
// Export CSV function
function exportFilteredCSV() {
  if (!filteredData.length) return;
  const fields = [
    "name",
    "operator",
    "city",
    "matched_county_name",
    "matched_county_fips",
    "state",
    "status",
    "mw",
    "investment",
    "county_winner",
    "trump_pct",
    "harris_pct",
    "margin_pct",
    "trump_votes",
    "harris_votes",
    "total_votes",
    "population_2024",
    "population_source",
  ];
  const quote = (v) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
  const csv = [
    fields.join(","),
    ...filteredData.map((f) => fields.map((k) => quote(f[k])).join(",")),
  ].join("\r\n");
  const url = URL.createObjectURL(
    new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "selected_data_centers.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
