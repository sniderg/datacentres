// Marker radius based on MW
function getMarkerRadius(mw, scaleMode) {
  if (scaleMode === "fixed" || !mw) return 7;
  // Scaled logarithmically or root
  return Math.max(6, Math.min(26, Math.sqrt(mw) * 0.45));
}

// Initialize Map
function initMap() {
  map = L.map("map", {
    center: [39.0, -96.5],
    zoom: 4,
    minZoom: 2,
    zoomSnap: 0.5,
    maxZoom: 14,
    scrollWheelZoom: false,
  });

  map.fitBounds([[24, -125], [50, -66]], { padding: [20, 20], maxZoom: 4 });

  // Base Tiles: Esri Light Gray Canvas (Keyless, clean, professional)
  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    {
      attribution: "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
      maxZoom: 16,
    },
  ).addTo(map);

  map.createPane("labels");
  map.getPane("labels").style.zIndex = 250;
  map.getPane("labels").style.pointerEvents = "none";

  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 16,
      pane: "labels",
    },
  ).addTo(map);

  markersLayer = L.layerGroup().addTo(map);

  // Enable scroll on click
  map.on("click", () => {
    map.scrollWheelZoom.enable();
  });
  map.on("mouseout", () => {
    map.scrollWheelZoom.disable();
  });
}

// Render Markers
function renderMapMarkers() {
  if (!map || !markersLayer) return;
  markersLayer.clearLayers();

  const scaleMode = document.getElementById("size-toggle").value;

  filteredData.forEach((f) => {
    if (f.lat == null || f.lon == null) return;

    const color = {
      "strong-trump": "#b91c1c",
      "lean-trump": "#ef4444",
      "lean-harris": "#3b82f6",
      "strong-harris": "#1d4ed8",
    }[politicalTier(f)];
    const radius = getMarkerRadius(f.mw, scaleMode);

    const marker = L.circleMarker([f.lat, f.lon], {
      radius: radius,
      fillColor: color,
      color: "#ffffff",
      weight: 1.5,
      opacity: 0.95,
      fillOpacity: 0.8,
    });

    // Rich Popup HTML
    const popupHtml = `
      <div class="dc-popup">
        <div class="dc-popup-title">${escapeHtml(f.name || "AI Data Center")}</div>
        <div class="dc-popup-op">Operator: <strong>${escapeHtml(f.operator || "Not specified")}</strong></div>
        
        <div class="dc-popup-pills">
          <span class="badge badge-${f.status || "operational"}">${f.status ? f.status.replace("_", " ") : "—"}</span>
          <span class="badge ${f.county_winner === "Trump" ? "badge-trump" : "badge-harris"}">${f.county_winner || "—"} County</span>
        </div>

        <div class="dc-popup-section">
          <div><strong>Location:</strong> ${escapeHtml([f.city, f.matched_county_name, f.state].filter(Boolean).join(", "))}</div>
          ${f.mw ? `<div><strong>Capacity:</strong> ${fmtNum(f.mw)} MW</div>` : ""}
          ${f.investment ? `<div><strong>Investment:</strong> ${fmtMoney(f.investment)}</div>` : ""}
          ${f.acres ? `<div><strong>Site Area:</strong> ${fmtNum(f.acres)} acres</div>` : ""}
        </div>

        <div class="dc-popup-vote ${f.county_winner === "Trump" ? "trump" : "harris"}">
          <div style="font-weight:700; font-size:0.84rem; margin-bottom:2px;">
            2024 Presidential Election: ${f.county_winner === "Trump" ? "Trump +" + f.margin_pct.toFixed(1) + "%" : "Harris +" + Math.abs(f.margin_pct).toFixed(1) + "%"}
          </div>
          <div style="font-size:0.78rem; color:#475569;">
            Trump: <strong>${fmtPct(f.trump_pct)}</strong> (${fmtNum(f.trump_votes)} votes)<br>
            Harris: <strong>${fmtPct(f.harris_pct)}</strong> (${fmtNum(f.harris_votes)} votes)<br>
            Total County Votes: ${fmtNum(f.total_votes)}
          </div>
        </div>
      </div>
    `;

    marker.bindPopup(popupHtml, { maxWidth: 320 });
    markersLayer.addLayer(marker);
  });

  // Update counter
  const totalMw = filteredData.reduce((acc, f) => acc + (f.mw || 0), 0);
  document.getElementById("map-counter").textContent =
    `Showing ${filteredData.length} of ${facilities.length} facilities (${fmtNum(Math.round(totalMw))} MW)`;
}
