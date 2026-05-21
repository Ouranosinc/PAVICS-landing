import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'assets', 'notebooks'))
OUTPUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'assets', 'datasets-notebooks.json'))

manifest = {}
for category in sorted([d for d in os.listdir(ROOT) if d.startswith('Datasets_') and os.path.isdir(os.path.join(ROOT, d))]):
    category_path = os.path.join(ROOT, category)
    subfolders = {}
    for dirpath, _, filenames in os.walk(category_path):
        rel = os.path.relpath(dirpath, category_path)
        if rel == '.':
            continue
        files = sorted([f for f in filenames if f.endswith('.html')])
        if files:
            subfolders[rel] = files
    manifest[category] = {
        'path': os.path.join('assets', 'notebooks', category).replace('\\', '/'),
        'subfolders': subfolders,
    }

with open(OUTPUT, 'w', encoding='utf-8') as fp:
    json.dump(manifest, fp, indent=2, ensure_ascii=False)

print(f'Wrote dataset manifest to {OUTPUT}')
