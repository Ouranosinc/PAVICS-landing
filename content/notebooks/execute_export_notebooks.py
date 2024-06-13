import shutil
import subprocess
from pathlib import Path

import git

repo = git.Repo(".", search_parent_directories=True)
repo = Path(repo.git_dir).parent

folders = dict(climate_indicators=False, hydrology=False)
for folder, run_flag in folders.items():
    for nb in [
        p
        for p in repo.joinpath(f"content/notebooks/{folder}").glob("*.ipynb")
        if "checkpoints" not in p.as_posix()
    ]:
        if run_flag:
            cmd = f"jupyter nbconvert --ExecutePreprocessor.timeout=6000 --to html --execute {nb.as_posix()}"
        else:
            cmd = f"jupyter nbconvert --to html {nb.as_posix()}"
        try:
            subprocess.run(cmd, shell=True, check=True)
            htmlfile = nb.parent.joinpath(nb.name.replace(".ipynb", ".html"))
            shutil.copyfile(
                htmlfile.as_posix(),
                repo.joinpath("src/assets/notebooks/")
                .joinpath(htmlfile.name)
                .as_posix(),
            )
        except:
            print(nb)
