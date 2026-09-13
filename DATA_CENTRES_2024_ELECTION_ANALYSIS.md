# Data centers, power & place: corrected methodology

Updated September 13, 2026. This replaces the earlier narrative, whose causal and population interpretations were unsupported.

The dashboard is the current interactive analysis. All summaries and charts follow its filters. The original facility/election snapshot is preserved; source election tallies have not been independently certified.

## Verified snapshot totals

- 474 tracked projects; 307 in Trump-won counties and 167 in Harris-won counties.
- 215,375.9 reported MW across 260 projects, including operational and cancelled records. This is not a total of newly installed capacity.
- Population matches 303 of 304 unique host counties (473 of 474 facilities).

## Population correction

Use Census Vintage 2024 July 1 resident estimates, joined by five-digit FIPS. Source: https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv

A uniform turnout adjustment is not appropriate: votes divided by eligible-voter turnout estimates eligible voters, not all residents. Population-weighted county vote shares are descriptive geographic indices, not estimated political preferences of nonvoters. Capacity × population is an exploratory weighting choice, not a burden measure.

New London County (09011) has no exact match in the current county-equivalent geography and is omitted from population calculations. No population is imputed. The manually entered North Slope election result remains unverified.

MW per 1,000 residents uses selected, population-matched projects with known MW. Its denominator counts each such county once. Incomplete MW coverage can understate capacity. Proposed capacity does not imply current consumption or environmental exposure.

## Categories and scope

Strong = winner receives at least 65% of all votes; lean = winner below 65%. Candidate vote-share charts retain other votes as gray. County presidential winners do not establish local political control. Project stages are a cross-sectional snapshot, not a historical migration series. Missing MW and investment remain missing.

## Reproduction

Run `python3 enrich_population.py` to join the retained Census file to `facilities_data.json` and rebuild `data.js`. Run `python3 build.py` for the deployable static output. `cross_reference.py` is the original live-source importer; it does not rebuild the JSON dashboard snapshot. Its joins use normalized names, not coordinate-based verification.
