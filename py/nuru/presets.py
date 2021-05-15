"""Manages configurable presets."""

import json
import glob
import logging
import os

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
    if i < len(presets):
        logging.info('Updating preset #%d: %s -> %s', i, presets[i], d)
        presets[i] = d
    else:
        for j in range(len(presets), i):
            dd = dict(name=f'#{j:03d}')
            logging.info('Creating empty preset #%d: %s', j, dd)
            presets.append(dd)
        logging.info('Adding preset #%d: %s', i, d)
        presets.append(d)
    json.dump(presets, open(PRESETS_PATH, 'w'), indent=2)
