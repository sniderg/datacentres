# Data centers, power & place

[Live dashboard](https://sniderg.github.io/datacentres/)

A static dashboard comparing a September 2026 snapshot of tracked U.S. data-center projects with 2024 county presidential election results and Census resident population. Source coverage and interpretation notes are on the page and in `DATA_CENTRES_2024_ELECTION_ANALYSIS.md`.

## Work on the site

No framework or package install is required. Run `python3 -m http.server 8765` and open `http://localhost:8765`. The page uses Leaflet, Chart.js and Google Fonts from external providers, so rendering the map and charts needs an internet connection.

| File | Responsibility |
| --- | --- |
| `index.html` | Semantic page structure and controls |
| `styles.css` | Shared design tokens, layout and responsive styles |
| `js/state.js` | Shared selection state and display formatting |
| `js/metrics.js` | Summary calculations and metric cards |
| `js/map.js` | Leaflet map, marker sizing and facility popups |
| `js/charts.js` | Four Chart.js comparisons |
| `js/table.js` | Facility rows, sorting, pagination rendering and CSV export |
| `js/app.js` | Filters and event handlers |
| `data.js` | Retained facility, election and population snapshot |

Scripts load in the explicit order in `index.html`, using deferred classic scripts so the site also works without a bundler. Keep calculation changes in `js/metrics.js`; keep layout changes in `styles.css`.

## Validate and publish

Run `node check_dashboard.cjs` for calculation and selection checks. Run `python3 build.py` to copy the deployable files into `dist/`. GitHub Pages currently serves the repository root on `main`, so pushing a reviewed commit to `main` publishes the same source directly. The optional `dist/` output is for other static hosts.

For visual changes, check the map, charts, filters, empty results, table and narrow-screen layout in a browser before publishing.

`enrich_population.py` rebuilds the population join from the retained Census CSV. The original live-source research scripts are retained for reference and are not run during deployment.
