"""Join Census Vintage 2024 resident population by county FIPS; never impute missing geography."""
import csv, json
from pathlib import Path
SOURCE = 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv'
rows = csv.DictReader(open('census_county_population_2024.csv', encoding='latin1'))
population = {r['STATE'] + r['COUNTY']: int(r['POPESTIMATE2024']) for r in rows if r['SUMLEV'] == '050'}
facilities = json.loads(Path('facilities_data.json').read_text())
for f in facilities:
    f['population_2024'] = population.get(str(f['matched_county_fips']).zfill(5))
    f['population_source'] = SOURCE if f['population_2024'] else None
Path('facilities_data.json').write_text(json.dumps(facilities, ensure_ascii=False))
Path('data.js').write_text('window.FACILITIES_DATA = ' + json.dumps(facilities, ensure_ascii=False) + ';\n')
print(f"Population matched for {sum(f['population_2024'] is not None for f in facilities)}/{len(facilities)} facilities")
