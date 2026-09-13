"""Build the static site without including research inputs or private files."""
from pathlib import Path
import shutil
Path('dist').mkdir(exist_ok=True)
for filename in ['index.html','data.js','dashboard.js','dashboard.css']:
    shutil.copyfile(filename, Path('dist') / filename)
print('Static site built in dist/')
