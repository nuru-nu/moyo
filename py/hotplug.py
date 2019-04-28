"""Hot plugs Python code into interactive environment / running scripts."""

import collections, importlib, os, traceback

import signals, hotplug_signals, util
import effects, hotplug_effects


# last module is the one with `.get_data()`
FileModules = collections.namedtuple('FileModules', ['file', 'modules'])
_MODULES = dict(
    signals=FileModules('hotplug_signals.py', [signals, hotplug_signals]),
    effects=FileModules('hotplug_effects.py', [effects, hotplug_effects]),
)


class HotPlugModule:
    def __init__(self, file_modules, logger):
        self.file_modules = file_modules
        self.logger = logger
        self.mtime = 0
        self.reload()

    def __dir__(self):
        return list(self.data.keys())

    def items(self):
        return self.data.items()

    def reload(self):
        path = self.path(self.file_modules.file)
        mtime = os.path.getmtime(path)
        if mtime > self.mtime:
            self.mtime = mtime
            try:
                for module in self.file_modules.modules:
                    importlib.reload(module)
                self.data = self.file_modules.modules[-1].get_data()
                self.logger.info(
                    'Reloaded {}'.format(self.file_modules.file))
            except Exception as e:
                self.logger.warn(
                    'Cannot eval {} : {}'.format(self.file_modules.file, e))
                print(traceback.format_exc())
            for k, v in self.data.items():
                setattr(self, k, v)

    def path(self, path):
        return os.path.join(os.path.dirname(__file__), path)


class HotPlug:
    def __init__(self, logger=util.NoLogger()):
        for name, file_modules in _MODULES.items():
            setattr(self, '_' + name, HotPlugModule(file_modules, logger))

    def __dir__(self):
        return _MODULES.keys()

    def __getattr__(self, key):
        module = getattr(self, '_{}'.format(key))
        module.reload()
        return module
