"""Manages configurable presets."""

import json
import os

from smanmi import util

logger = util.createLogger('presets')

NCA_PATH = os.path.join(os.path.dirname(__file__), 'nca.json')


def get_nca():
    return json.load(open(NCA_PATH))


def set_nca(name, d):
    nca = get_nca()
    if name in nca['presets']:
        logger.info('Updating NCA "%s"', name)
    else:
        logger.info('Adding NCA "%s"', name)
    nca['presets'][name] = d
    json.dump(nca, open(NCA_PATH, 'w'))
