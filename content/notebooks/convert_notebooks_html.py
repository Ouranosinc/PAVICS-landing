import subprocess
from pathlib import Path
for nb in [p  for p in Path('.').rglob('*.ipynb') if 'checkpoints' not in p.as_posix()]:
    cmd = f"jupyter nbconvert --ExecutePreprocessor.timeout=600 --to html --execute {nb.as_posix()}"
    try:
        subprocess.run(cmd, shell=True, check=True)
    except:
        print(nb)