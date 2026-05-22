import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent.joinpath('src', 'assets', 'notebooks') #os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'assets', 'notebooks'))
OUTPUT = ROOT.parent.joinpath('datasets-notebooks.json') #os.path.abspath(os.path.join(ROOT, '..', 'dataset_manifest.json'))

manifest = {}



for category in sorted([d for d in ROOT.iterdir() if d.name.startswith('Datasets_') and d.is_dir()]):
    print(f'Processing category: {category.name}')
    
    subfolders = {}

    all_subdirs = sorted([d for d in category.iterdir() if d.is_dir()])
    subdirs = [d for d in all_subdirs if 'Ouranos' in d.name ]
    subdirs.extend([d for d in all_subdirs if 'Environment and Climate Change Canada' in d.name ])
    subdirs.extend([d for d in all_subdirs if d not in subdirs])
    for dirpath in subdirs:
        filenames = [f.name for f in dirpath.iterdir() if f.is_file()]
        files = sorted([f for f in filenames if f.endswith('.html')])
        
        sort_order = ['CRCM5-CMIP6', 'ESPO-G6-R2 v1.0.0 _ Ouranos', 'ESPO-G6-R2 v1.0.0 _ Derived', 'ESPO-G6-E5L', 'PINS', 'ClimEX', 'CanDCS-M6']
        files.sort(key=lambda x: sort_order.index(next((s for s in sort_order if s in x), '')) if any(s in x for s in sort_order) else len(sort_order))

        if files:
            subfolders[dirpath.name] = files
    manifest[category.name] = {
        'path': Path('assets', 'notebooks', category.name).as_posix(),
        'subfolders': subfolders,
    }

with open(OUTPUT, 'w', encoding='utf-8') as fp:
    json.dump(manifest, fp, indent=2, ensure_ascii=False)

print(f'Wrote dataset manifest to {OUTPUT}')
