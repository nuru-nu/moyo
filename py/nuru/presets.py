"""Manages configurable presets."""

import copy
import json
import glob
import logging
import os
import time

from smanmi import util

PRESETS_PATH = os.path.join(os.path.dirname(__file__), 'presets.json')
NCA_GLOB = os.path.join(
    os.path.dirname(__file__),
    os.path.pardir,
    os.path.pardir,
    'nca',
    f'*.npy',
)


def load():
    ret = json.load(open(PRESETS_PATH))
    ret['ncas'] = [path.split('/')[-1][:-4] for path in glob.glob(NCA_GLOB)]
    return ret


def update(i, d):
    presets = load()
    anims = presets['animations']
    now = time.strftime('%Y%m%d_%H%M')
    d = copy.deepcopy(d)
    d['mtime'] = now
    if i < len(anims):
        logging.info('Updating preset #%d: %s -> %s', i, anims[i], d)
        anims[i] = d
    else:
        d['ctime'] = now
        for j in range(len(anims), i):
            dd = dict(name=f'#{j:03d}', ctime=now, mtime=now)
            logging.info('Creating empty preset #%d: %s', j, dd)
            anims.append(dd)
        logging.info('Adding preset #%d: %s', i, d)
        anims.append(d)
    del presets['ncas']
    json.dump(presets, open(PRESETS_PATH, 'w'), indent=2)
