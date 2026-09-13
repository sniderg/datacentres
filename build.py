"""Build the static site without including research inputs or private files."""
from pathlib import Path
import shutil
Path('dist').mkdir(exist_ok=True)
for filename in ['index.html','data.js','styles.css']:
    shutil.copyfile(filename, Path('dist') / filename)
shutil.copytree('js', 'dist/js', dirs_exist_ok=True)
print('Static site built in dist/')
