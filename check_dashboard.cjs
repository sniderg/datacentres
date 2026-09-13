const fs = require("fs"),
  vm = require("vm"),
  assert = require("assert");
const elements = {};
const el = (id) =>
  (elements[id] ??= {
    value: [
      "winner-filter",
      "status-filter",
      "tier-filter",
      "operator-filter",
    ].includes(id)
      ? "all"
      : "",
    innerHTML: "",
    textContent: "",
    getContext: () => ({}),
    appendChild() {},
    addEventListener() {},
  });
const context = vm.createContext({
  console,
  window: {},
  document: {
    getElementById: el,
    querySelectorAll: () => [],
    createElement: () => ({ addEventListener() {} }),
    addEventListener() {},
  },
  Chart: class {
    constructor(c, o) {
      this.data = o.data;
    }
    destroy() {}
  },
});
for (const path of [
  "data.js",
  "js/state.js",
  "js/metrics.js",
  "js/map.js",
  "js/table.js",
  "js/charts.js",
  "js/app.js",
])
  vm.runInContext(fs.readFileSync(path, "utf8"), context);
vm.runInContext(
  `
applyFilters(); if(filteredData.length!==474 || filteredData[0].mw!==10000) throw Error('initial count or sorting');
if(calculateSummary(filteredData).popCounties.length!==303) throw Error('population coverage');
for(const f of facilities) if(politicalTier(f).endsWith('harris') !== (f.county_winner==='Harris')) throw Error('tier');
document.getElementById('status-filter').value='operational';applyFilters();if(filteredData.length!==124)throw Error('status');
if(chartStatus.data.datasets.reduce((a,d)=>a+d.data.reduce((x,y)=>x+y,0),0)!==124)throw Error('chart scope');
document.getElementById('search-input').value='no such facility xyz';applyFilters();if(filteredData.length!==0 || document.getElementById('summary-cards').innerHTML.includes('NaN'))throw Error('empty');
document.getElementById('search-input').value='';document.getElementById('status-filter').value='all';applyFilters();if(filteredData.length!==474)throw Error('reset');
console.log('PASS: totals, population coverage, tier consistency, sorted rows, filter/chart reconciliation, empty state and reset');
`,
  context,
);
