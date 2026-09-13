// Global state
let facilities = window.FACILITIES_DATA || [];
let filteredData = [...facilities];
let currentPage = 1;
const pageSize = 20;
let sortField = "mw";
let sortDirection = "desc";

// Leaflet Map instance & layer group
let map = null;
let markersLayer = null;
let chartStatus = null;
let chartCapacity = null;
let chartStates = null;
let chartOperators = null;

// Helpers
const fmtNum = (n) => (n != null ? Number(n).toLocaleString("en-US") : "—");
const fmtMoney = (n) => {
  if (n == null) return "—";
  if (n >= 1e9) return "$" + (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return "$" + Math.round(n / 1e6) + "M";
  return "$" + Number(n).toLocaleString("en-US");
};
const fmtPct = (n) => (n != null ? Number(n).toFixed(1) + "%" : "—");
function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, function (m) {
    return {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[m];
  });
}
