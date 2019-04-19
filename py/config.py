"""Common config, backed by ./config.json."""

import fcntl, json, os, sys

import util


class DataDiff:
    def __init__(self, data):
        if data is not None:
            data = dict(**data)
        self.data = data

    def log_diff(self, data, logger):
        if self.data is None:
            return ''
        removed, changed, added = set(self.data.keys()), set(), set()
        for k, v in self.data.items():
            if k in removed:
                removed.remove(k)
            if k not in self.data:
                added.add(k)
            elif v != data[k]:
                changed.add(k)
        diffs = '; '.join([
            '{} {}'.format(n, s)
            for n, s in (
                ('removed', removed),
                ('added', added),
                ('changed', changed)
            )
            if s
        ])
        if diffs:
            logger.info('re-read config : {}'.format(diffs))


class Config:

    def __init__(self, logger):
        self.logger = logger
        self.path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.mtime = 0
        self.data = None
        self.read(log_diffs=False)

    def read(self, log_diffs=True):
        mtime = os.stat(self.path).st_mtime
        if mtime <= self.mtime:
            return
        with open(self.path) as f:
            differ = DataDiff(self.data)
            try:
                fcntl.lockf(f, fcntl.LOCK_SH)
                self.data = json.load(open(self.path))
                self.mtime = mtime
            finally:
                fcntl.lockf(f, fcntl.LOCK_UN)
            differ.log_diff(self.data, self.logger)

    def write(self):
        with open(self.path, 'w') as f:
            try:
                fcntl.lockf(f, fcntl.LOCK_EX)
                json.dump(self.data, f)
            finally:
                fcntl.lockf(f, fcntl.LOCK_UN)

    def keys(self):
        self.read()
        return list(self.data.keys())

    def get(self, key, default):
        key = str(key)
        self.read()
        return self.data.get(key, default)

    def __getitem__(self, key):
        key = str(key)
        self.read()
        return self.data[key]

    def __setitem__(self, key, value):
        self.read()
        key = str(key)
        if key in self.data and self.data[key] == value:
            return
        self.data[key] = value
        self.logger.info('config[{}]={}'.format(key, value))
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
            print('-> keys:', ' '.join(conf.keys()))
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
