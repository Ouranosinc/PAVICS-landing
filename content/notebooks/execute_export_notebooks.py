import subprocess
from pathlib import Path
import shutil
import git
import requests
repo = git.Repo('.', search_parent_directories=True)
repo = Path(repo.git_dir).parent
raven_nbs = ['https://raw.githubusercontent.com/Ouranosinc/raven/master/docs/source/notebooks/Model_calibration.ipynb',
             'https://raw.githubusercontent.com/Ouranosinc/raven/master/docs/source/notebooks/Extract_geographical_watershed_properties.ipynb',
             'https://raw.githubusercontent.com/Ouranosinc/raven/master/docs/source/notebooks/Running_hydrological_models_on_a_remote_server.ipynb',
             'https://raw.githubusercontent.com/Ouranosinc/raven/master/docs/source/notebooks/Hydrological_realtime_forecasting.ipynb',
             'https://raw.githubusercontent.com/Ouranosinc/raven/master/docs/source/notebooks/time_series_analysis.ipynb'
             ]
for nb in raven_nbs:
    directory = repo.joinpath('content/notebooks/hydrology')
    filename = directory.joinpath(nb.split('/')[-1])
    r = requests.get(nb)

    with open(filename, 'wb') as f:
        f.write(r.content)
        f.close()

folders = dict(climate_indicators=False, hydrology=False)
#run_flag = False #execute notebooks before conversion?
for folder, run_flag in folders.items():
    for nb in [p  for p in repo.joinpath(f'content/notebooks/{folder}').glob('*.ipynb') if 'checkpoints' not in p.as_posix()]:
        if run_flag:
            cmd = f"jupyter nbconvert --ExecutePreprocessor.timeout=6000 --to html --execute {nb.as_posix()}"
        else:
            cmd = f"jupyter nbconvert --to html {nb.as_posix()}"
        try:
            subprocess.run(cmd, shell=True, check=True)
            htmlfile = nb.parent.joinpath(nb.name.replace('.ipynb','.html'))
            shutil.copyfile(htmlfile.as_posix(), repo.joinpath('src/assets/notebooks/').joinpath(htmlfile.name).as_posix())
        except:
            print(nb)




