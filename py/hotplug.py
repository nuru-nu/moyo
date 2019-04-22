"""Hot plugs Python code into interactive environment / running scripts."""

import importlib, os

import signals as S, util  # NOQA


logger = util.createLogger('hotplug')


class HotPlugModule:
    def __init__(self, path):
        self.path = path
        self.mtime = 0
        self.reload()

    def __dir__(self):
        return list(self.data.keys())

    def items(self):
        return self.data.items()

    def reload(self):
        mtime = os.path.getmtime(self.path)
        if mtime > self.mtime:
            self.mtime = mtime
            with open(self.path, 'r') as f:
                try:
                    importlib.reload(S)
                    self.data = eval(f.read())
                    logger.info('Reloaded {}'.format(self.path))
                except Exception as e:
                    logger.warn('Cannot eval {} : {}'.format(self.path, e))
            for k, v in self.data.items():
                setattr(self, k, v)


class HotPlug:
    def __init__(self):
        self._signals = HotPlugModule(self.path('hotplug_signals.py'))

    def path(self, path):
        return os.path.join(os.path.dirname(__file__), path)

    def __dir__(self):
        return ['signals']

    def __getattr__(self, key):
        module = getattr(self, '_{}'.format(key))
        module.reload()
        return module
