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
  "model_data.js",
  "js/state.js",
  "js/metrics.js",
  "js/map.js",
  "js/table.js",
  "js/charts.js",
  "js/outlook.js",
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
const corrected = Object.fromEntries(facilities.filter(f=>['08041','17037','29095'].includes(String(f.matched_county_fips).padStart(5,'0'))).map(f=>[String(f.matched_county_fips).padStart(5,'0'),f]));
if(corrected['08041'].trump_votes!==203933 || corrected['17037'].county_winner!=='Harris' || corrected['29095'].harris_votes!==187026)throw Error('official election corrections');
const scenarios=window.PIPELINE_MODEL.scenarios;
for(const scenario of ['neutral','proportional','winner_step']){
  let last=-Infinity;
  for(const year of window.PIPELINE_MODEL.years){
    const value=scenarios[scenario][year].Trump.operating_gw.median;
    if(value<last)throw Error('nonmonotonic outlook');
    last=value;
  }
}
const ratio=scenarios.proportional['2030']['Trump/Harris'].intensity_ratio.median;
if(Math.abs(ratio-3.582238680852066)>1e-10)throw Error('2030 proportional ratio');
console.log('PASS: observed totals, corrections, filters, charts and modelled outlook reconciliation');
`,
  context,
);
