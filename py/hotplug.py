"""Hot plugs Python code into interactive environment / running scripts."""

import importlib, os, traceback

import signals as S, util  # NOQA


class HotPlugModule:
    def __init__(self, path, logger):
        self.path = path
        self.logger = logger
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
                    self.logger.info('Reloaded {}'.format(self.path))
                except Exception as e:
                    self.logger.warn(
                        'Cannot eval {} : {}'.format(self.path, e))
                    print(traceback.format_exc())
            for k, v in self.data.items():
                setattr(self, k, v)


class HotPlug:
    def __init__(self, logger=util.NoLogger()):
        self._signals = HotPlugModule(self.path('hotplug_signals.py'), logger)

    def path(self, path):
        return os.path.join(os.path.dirname(__file__), path)

    def __dir__(self):
        return ['signals']

    def __getattr__(self, key):
        module = getattr(self, '_{}'.format(key))
        module.reload()
        return module
