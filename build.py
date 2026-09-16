"""Build the static site without including research inputs or private files."""
from pathlib import Path
import shutil
Path('dist').mkdir(exist_ok=True)
for filename in ['index.html','data.js','model_data.js','styles.css']:
    shutil.copyfile(filename, Path('dist') / filename)
shutil.copytree('js', 'dist/js', dirs_exist_ok=True)

Path('dist/assets').mkdir(exist_ok=True)
shutil.copyfile(
    'analysis/capacity_model.svg',
    'dist/assets/capacity_model.svg',
)

Path('dist/analysis/sources').mkdir(parents=True, exist_ok=True)
for filename in [
    'county_pipeline_review.html',
    'capacity_model.svg',
    'capacity_model.dot',
    'election_corrections.json',
    'pipeline_model.py',
]:
    shutil.copyfile(Path('analysis') / filename, Path('dist/analysis') / filename)
for filename in ['manifest.json', 'projects.json']:
    shutil.copyfile(
        Path('analysis/sources') / filename,
        Path('dist/analysis/sources') / filename,
    )
print('Static site built in dist/')
