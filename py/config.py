
from __future__ import print_function
import json, fcntl, os


CHANNELS = [
        # REAL channels
        'intensity',
        'strobe',
        'red',
        'green',
        'blue',
        'white',
        'pan',
        'tilt',
        'speed',
        # PSEUDO channels
        'move amp',
        'move freq',
        'pulse amp',
        'pulse freq',
        ]
CHANNELS_REAL = 9

#  pan : 0=148: 0
#        37=184: pi/2
#        72=221: pi
#        109=255: 3pi/2
#  tilt: 38: 0
#        86: pi/4
#        133: pi/2
#        191: 3pi/4
#        229: pi
INITIAL_VALUES = dict(
        intensity=255,
        white=255,
        pan=72,
        tilt=133
        )


class Config(object):

    def __init__(self):
        self.path = 'config.json'
        self.mtime = 0
        self.read()
        if 'presets' not in self.data:
            self.data['presets'] = {}

    def read(self):
        mtime = os.stat(self.path).st_mtime
        if mtime <= self.mtime:
            return
        with open(self.path) as f:
            try:
                fcntl.lockf(f, fcntl.LOCK_SH)
                self.data = json.load(open(self.path))
                self.mtime = mtime
            finally:
                fcntl.lockf(f, fcntl.LOCK_UN)

    def write(self):
        with open(self.path, 'w') as f:
            try:
                fcntl.lockf(f, fcntl.LOCK_EX)
                json.dump(self.data, f)
            finally:
                fcntl.lockf(f, fcntl.LOCK_UN)

    def getpreset(self, key):
        key = str(key)  # javascript dictionaries ...
        self.read()
        preset = dict(zip(CHANNELS, [0]*len(CHANNELS)))
        preset.update(**INITIAL_VALUES)
        preset.update(**self.data['presets'].get(key, {}))
        return preset

    def setpreset(self, key, value):
        key = str(key)
        self.data['presets'][key] = value
        self.write()

    def get(self, key, default):
        key = str(key)
        self.read()
        return self.data.get(key, default)

    def set(self, key, value):
        key = str(key)
        self.data[key] = value
        self.write()


conf = Config()


if __name__ == '__main__':
    import readline, sys

    while True:
        sys.stdout.write('>>> ')
        sys.stdout.flush()
        words = sys.stdin.readline().strip().split(' ')

        if words == ['quit']:
            break
        elif words == ['list']:
            print('-> ', conf.data.keys())
        elif words[0] == 'get' and len(words) == 2:
            print('-> ', conf.get(words[1], '?'))
        elif words[0] == 'set' and len(words) == 3:
            value = words[2]
            try:
                value = int(value)
                print('-> int(%d)' % value)
            except ValueError:
                try:
                    value = float(value)
                    print('-> float(%f)' % value)
                except ValueError:
                    print('-> str(%s)' % value)
            conf.set(words[1], value)
        elif words == ['listpresets']:
            print('-> ', ', '.join(sorted(conf.data['presets'].keys())))
        elif words[0] == 'getpreset' and len(words) == 2:
            print('-> ', ', '.join(conf.getpreset(words[1])))
        elif words == ['help']:
            print('')
            print('list')
            print('get KEY')
            print('set KEY VALUE')
            print('list')
            print('getpreset PRESET')
            print('quit')
            print('')
        else:
            print('*** unknown command - try "help"')

