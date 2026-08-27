import fnmatch
import json
import os
import shutil
import subprocess
from pathlib import Path

repo = (
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.STDOUT
    )
    .decode("utf-8")
    .strip()
)
ROOT = Path(
    __file__
).parent  # os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'assets', 'notebooks'))
OUTPUT = Path(repo).joinpath(
    "src", "assets", "datasets-notebooks.json"
)  # os.path.abspath(os.path.join(ROOT, '..', 'dataset_manifest.json'))

manifest = {}

for category in sorted(
    [d for d in ROOT.iterdir() if d.name.startswith("Datasets_") and d.is_dir()]
):
    print(f"Processing category: {category.name}")

    subfolders = {}

    all_subdirs = sorted([d for d in category.iterdir() if d.is_dir()])
    
    if "Reanalysis" in category.name:
        order = [
            "Environment and Climate Change Canada",
            "ECMWF",
            "Ouranos"
        ]
        subdirs = []
    else:
        subdirs = [d for d in all_subdirs if "Ouranos" in d.name]
        order = [
            "Environment and Climate Change Canada",
            "Canadian Centre for Climate Services",
            "PCIC",
        ]
    for o in order:
        subdirs.extend([d for d in all_subdirs if o in d.name and d not in subdirs])

    subdirs.extend([d for d in all_subdirs if d not in subdirs])
    for dirpath in subdirs:
        filenames = [f.name for f in dirpath.iterdir() if f.is_file()]
        files = sorted([f for f in filenames if f.endswith(".html")])

        sort_order = [
            "CRCM5-CMIP6*daily",
            "CRCM5-CMIP6* hourly",
            "CRCM5-CMIP6*3-hourly",
            "CRCM5-CMIP6*monthly",
            "CRCM5-CMIP6*",
            "ESPO-G6-R2 v1.0.0 _ Ouranos",
            "ESPO-G6-R2 v1.0.0 _ Derived",
            "ESPO-G6-E5L",
            "ESPO",
            "PINS",
            "ClimEX",
            "CanDCS-M6",
            "Homogenized Daily Temp*",
            "Daily Adjusted Prec*",
            "PCIC*",
            "NRCanMet*",
            "NRCAN*",
        ]

        def sort_key(x):
            normalized = x.lower()
            match = next(
                (
                    pattern
                    for pattern in sort_order
                    if fnmatch.fnmatch(normalized, f"*{pattern.lower()}*")
                ),
                None,
            )
            group_index = (
                sort_order.index(match) if match is not None else len(sort_order)
            )
            return (group_index, normalized)

        files.sort(key=sort_key)

        outname = dirpath.name.replace(
            "Ouranos Consortium on Regional Climatology and Adaptation to Climate Change",
            "Ouranos",
        )
        if files:
            subfolders[outname] = files
        shutil.copytree(
            dirpath,
            OUTPUT.parent.joinpath("notebooks", category.name, outname),
            dirs_exist_ok=True,
        )
    manifest[category.name] = {
        "path": Path("assets", "notebooks", category.name).as_posix(),
        "subfolders": subfolders,
    }


with open(OUTPUT, "w", encoding="utf-8") as fp:
    json.dump(manifest, fp, indent=2, ensure_ascii=False)

print(f"Wrote dataset manifest to {OUTPUT}")
