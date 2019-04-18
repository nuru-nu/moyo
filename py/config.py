"""Common config, backed by ./config.json."""

import fcntl, json, os, sys

import util


class Config:

    def __init__(self, logger):
        self.logger = logger
        self.path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.mtime = 0
        self.read()

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

    def get(self, key, default):
        key = str(key)
        self.read()
        return self.data.get(key, default)

    def __getitem__(self, key):
        key = str(key)
        self.read()
        return self.data[key]

    def __setitem__(self, key, value):
        key = str(key)
        self.data[key] = value
        self.write()

    def __delitem__(self, key):
        del self.data[key]
        self.write()


if __name__ == '__main__':

    logger = util.createLogger('config')
    conf = Config(logger)

    while True:
        sys.stdout.write('>>> ')
        sys.stdout.flush()
        words = sys.stdin.readline().strip().split(' ')

        if words == ['quit']:
            break
        elif words == ['list']:
            print('-> keys:', ' '.join(conf.data.keys()))
        elif words[0] == 'get' and len(words) == 2:
            print('-> ', conf[words[1]])
        elif words[0] == 'del' and len(words) == 2:
            del conf[words[1]]
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
            conf[words[1]] = value
        elif words == ['help']:
            print('')
            print('list')
            print('get KEY')
            print('del KEY')
            print('set KEY VALUE')
            print('quit')
            print('')
        else:
            print('*** unknown command - try "help"')
