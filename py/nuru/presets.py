"""Manages configurable presets."""

import json
import glob
import os

from smanmi import util

logger = util.createLogger('presets')

NCA_PATH = os.path.join(os.path.dirname(__file__), 'nca.json')
NCA_GLOB = os.path.join(
    os.path.dirname(__file__),
    os.path.pardir,
    os.path.pardir,
    'nca',
    f'*.npy',
)


def _upgrade_presets(presets):
    ret = {}
    for k, v in presets.items():
        if isinstance(v, str):
            v = dict(nca=v)
        # if '_emotion' not in v and '_' in k:
        #     v['_emotion'] = k.split('_')[-1]
        ret[k] = v
    return ret


def get_nca():
    ret = json.load(open(NCA_PATH))
    ret['presets'] = _upgrade_presets(ret['presets'])
    ret['all_names'] = [path.split('/')[-1][:-4] for path in glob.glob(NCA_GLOB)]
    return ret


def set_nca(name, d):
    nca = get_nca()
    if name in nca['presets']:
        logger.info('Updating NCA "%s"', name)
    else:
        logger.info('Adding NCA "%s"', name)
    nca['presets'][name] = d
    json.dump(nca, open(NCA_PATH, 'w'))
