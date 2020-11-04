
import glob
import json
import os

root = os.path.dirname(__file__)
if root: root = root + '/'

data = {}
for directory in glob.glob(f'{root}sequences/*'):
    if not os.path.isdir(directory): continue
    d = data[os.path.basename(directory)] = []
    for path in sorted(glob.glob(f'{directory}/*.JPG')):
        d.append('/'.join(path.split('/')[-3:]))

print(json.dumps(data))