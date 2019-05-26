"""Building blocs for signals etc.

Synoposis:

  import signals as S

  class A(S.Signal):
    def init(mult):
        pass
    def call(self, value):
        return value * self.mult

  class B(S.Signal):
    def call(self, in1, in2):
        return dict(value=in1 + in2)

  runner = S.SignalRunner(dict(a=A(mult=3, b=B())), ['in1', 'in2'])
  values = runner(in1=1, in2=2)
  print(values['a'])
"""

import inspect

# Base classes
###############################################################################


class D:
    """Helper class for attribute access to dictionary."""
    def __init__(self, **kw):
        self.kw = kw

    def __dir__(self):
        return self.kw.keys()

    def __getattr__(self, key):
        return getattr(self, 'kw')[key]

    def __repr__(self):
        return repr(self.kw)


class Signal:
    """Provides |, wants, params."""

    def __init__(self, *args, **params):
        self.wants = inspect.getfullargspec(self.call).args[1:]
        self.params = params.keys()
        if hasattr(self, 'init'):
            if args:
                names = inspect.getfullargspec(self.init).args[1:]
                params.update(zip(names, args))
            self.init(**params)
        for k, v in params.items():
            assert not hasattr(self, k)
            setattr(self, k, v)

    def __or__(self, other):
        return SignalChain(self, other)

    def __mul__(self, other):
        return SignalMult(self, other)

    def __call__(self, **allkw):
        kw = {k: allkw[k] for k in self.wants}
        ret = self.call(**kw)
        if not isinstance(ret, dict):
            ret = dict(value=ret, **{
                k: allkw[k]
                for k in allkw
                if k != 'value'
            })
        return ret

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            ','.join([
                '{}={}'.format(p, getattr(self, p))
                for p in self.params
            ]))


class SignalLast(Signal):
    """Provides lastin, lastout."""

    def __call__(self, **allkw):
        kw = {k: allkw[k] for k in self.wants}
        if not hasattr(self, 'lastin'):
            self.lastin = self.lastout = D(**kw)
        lastin = D(**kw)
        ret = super().__call__(**allkw)
        self.lastin = lastin
        self.lastout = D(**ret)
        return ret


class SignalChain(Signal):

    def __init__(self, sig1, sig2):
        self.wants = sig1.wants
        self.sig1 = sig1
        self.sig2 = sig2
        nsigs1 = sig1.nsigs if isinstance(sig1, SignalChain) else 1
        nsigs2 = sig2.nsigs if isinstance(sig2, SignalChain) else 1
        self.nsigs = nsigs1 + nsigs2

    def recurse(self):
        for sig in (self.sig1, self.sig2):
            if isinstance(sig, SignalChain):
                for sigsig in sig.recurse():
                    yield sigsig
                continue
            yield sig

    def __call__(self, **kw):
        return self.sig2(**self.sig1(**kw))

    def __repr__(self):
        return ' | '.join([repr(self.sig1), repr(self.sig2)])


class SignalMult(SignalChain):

    def __init__(self, sig1, sig2):
        super().__init__(sig1, sig2)
        self.wants = list(set(sig1.wants).union(sig2.wants))

    def __call__(self, **kw):
        values1 = self.sig1(**kw)
        values2 = self.sig2(**kw)
        return {
            k: values1[k] * values2[k]
            for k in set(values1).intersection(values2)
            if (
                isinstance(values1[k], (int, float, complex)) and
                isinstance(values2[k], (int, float, complex))
            )
        }

    def __repr__(self):
        return ' * '.join([repr(self.sig1), repr(self.sig2)])


# Basic signals
###############################################################################

class Named(Signal):

    def __init__(self, name):
        # Overwrite so we can specify positional arguments
        super().__init__(name=name)
        self.wants = (name,)

    def call(self, **kw):
        return kw[self.name]


# SignalRunner
###############################################################################


def make_order(signals, provided):
    """Returns ordered keys of `signals` satisfying their wants."""
    ordered = []
    provided = set(provided)
    names = set(signals.keys())
    while names:
        done = set()
        for name in names:
            signal = signals[name]
            if len(provided.intersection(signal.wants)) == len(signal.wants):
                done.add(name)
        assert done, 'could not satisfy ANY of {}'.format(
            ', '.join([
                '{}->{}'.format(signals[name], signals[name].wants)
                for name in names
            ])
        )
        names = names.difference(done)
        provided = provided.union(done)
        ordered += list(done)
    return ordered


class SignalRunner:
    """Runs signals DAG."""

    def __init__(self, signals, provided):
        self.signals = signals
        self.provided = provided
        self.ordered = make_order(signals, provided)

    def __call__(self, **kw):
        values = dict(**kw)
        for name in self.ordered:
            values[name] = self.signals[name](**values)['value']
        return values
