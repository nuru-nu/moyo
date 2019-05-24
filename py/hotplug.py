"""Hot plugs Python code into interactive environment / running scripts."""

import collections, importlib, os, time, traceback

import util

import effects, hotplug_effects
import pixel_functions, animations, hotplug_animations

has_signals = False
try:
    import signals, hotplug_signals
    has_signals = True
except ImportError as e:
    print('COULD NOT LOAD signals :', e)
except ModuleNotFoundError as e:
    print('COULD NOT LOAD signals :', e)


# last module is the one with `.get_data()`
FileModules = collections.namedtuple('FileModules', ['file', 'modules'])
_MODULES = dict(
    effects=FileModules('hotplug_effects.py', [effects, hotplug_effects]),
    animations=FileModules('hotplug_animations.py', [
        pixel_functions, animations, hotplug_animations]),
)

if has_signals:
    _MODULES['signals'] = FileModules(
        'hotplug_signals.py', [signals, hotplug_signals])


class HotPlugModule:
    def __init__(self, file_modules, logger, dt_min_s=1):
        self.file_modules = file_modules
        self.logger = logger
        self.mtime = 0
        self.t0 = 0
        self.dt_min_s = dt_min_s
        self.reload()

    def __dir__(self):
        return list(self.data.keys())

    def items(self):
        return self.data.items()

    def reload(self):
        if time.time() - self.t0 < self.dt_min_s:
            return
        self.t0 = time.time()
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
