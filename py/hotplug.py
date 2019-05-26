"""Hot plugs Python code into interactive environment / running scripts."""

import collections, os, time, traceback
import importlib  # noqa: F401

import util


# files to watch and modules to (re)load
# last module is the one with `.get_data()`
FileModules = collections.namedtuple('FileModules', ['files', 'modules'])
_MODULES = dict(
    effects=FileModules(['hotplug_effects.py', 'effects.py'],
                        ['effects', 'hotplug_effects']),
    animations=FileModules(['hotplug_animations.py', 'animations.py'],
                           ['pixel_functions', 'animations',
                            'hotplug_animations']),
    signals=FileModules(['hotplug_signals.py', 'signals.py'],
                        ['signals', 'hotplug_signals']),
)


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
        mtime = max([
            os.path.getmtime(self.path(filename))
            for filename in self.file_modules.files
        ])
        if mtime > self.mtime:
            try:
                for module in self.file_modules.modules:
                    if self.mtime == 0:
                        exec('import {}'.format(module))
                    exec('importlib.reload({})'.format(module))
                self.data = eval(self.file_modules.modules[-1]).get_data()
                self.logger.info(
                    'Reloaded {}'.format(self.file_modules.files))
            except Exception as e:
                self.logger.warn(
                    'Cannot eval {} : {}'.format(self.file_modules.files, e))
                print('-' * 72)
                print(traceback.format_exc())
                print('-' * 72)
            for k, v in self.data.items():
                setattr(self, k, v)
            self.mtime = mtime

    def path(self, path):
        return os.path.join(os.path.dirname(__file__), path)


class HotPlug:
    def __init__(self, logger=util.NoLogger(), modules=()):
        _modules = []
        for name, file_modules in _MODULES.items():
            if modules and name not in modules:
                continue
            module = HotPlugModule(file_modules, logger)
            module.reload()
            _modules.append(name)
            setattr(self, '_' + name, module)
        setattr(self, '_modules', _modules)

    def __dir__(self):
        return getattr(self, '_modules')

    def __getattr__(self, key):
        if key not in getattr(self, '_modules'):
            return AttributeError('HotPlug "{}" not set'.format(key))
        key = '_{}'.format(key)
        module = getattr(self, key)
        module.reload()
        return module
