import glob

import scipy

import effects as E, logic as L, settings, util


_get_sample_cache = {}
def get_sample(partial, rate):
    global _get_sample_cache
    key = '{} {}'.format(partial, rate)
    if not key in _get_sample_cache:
        pattern = '../data/samples/{}/*{}*.wav'.format(rate, partial)
        paths = glob.glob(pattern)
        assert len(paths) == 1, '{} matches {}'.format(partial, paths)
        sr, wav = scipy.io.wavfile.read(paths[0])
        assert sr == rate
        _get_sample_cache[key] = util.int16_to_float(wav)
    return _get_sample_cache[key]


def gs1(partial):
    return get_sample(partial, rate=settings.out1_rate)


def gs2(partial):
    return get_sample(partial, rate=settings.out2_rate)


def get_data():
    return dict(
        effector1=E.Effector(settings.out1_rate, [
            # E.Delay(1) | E.Echo(0.2, 0.9) | E.SigAmp('ios'),
            # E.Echo(0.3, 0.8) | E.SigAmp('iso2'),
            # E.SilenceOrPlaying(),

            E.RndPlay(gs1('haunting'), 'left_drone'),
            E.RndPlay(gs1('haunting'), 'right_drone'),
            # E.Silence(),
            # E.RndPlay(gs1('synthy'), 'left_drone'),

            # E.RndPlay(gs1('muffled-thunderstorm'), 'right_drone') | E.Compressor(30),
            # E.RndPlay(gs1('muffled-thunderstorm'), 'left_drone') | E.Compressor(50),

            # E.RndPlay(haunted_wav, 'bass_ooo'),
            # E.Sinusoidal(50) | E.SigAmp('low'),
            # E.Sinusoidal(400) | E.SigAmp('high'),
            # E.Silence(),
            # E.Silence(),
            # E.RndSub(
            #     haunted_wav,
            #     sample_minmax=[3, 8],
            #     break_minmax=[1, 20],
            #     ramp_minmax=[2, 4]),
            # E.RndSub(
            #     haunted_wav,
            #     sample_minmax=[3, 8],
            #     break_minmax=[1, 20],
            #     ramp_minmax=[2, 4]),
        ]),
        effector2=E.Effector(settings.out2_rate, [
            # E.RndPlay(gs2('rain-and-thunderstorm'), 'left_drone'),
            # E.RndPlay(gs2('rain-and-thunderstorm'), 'right_drone'),
            # E.RndPlay(haunted2_wav, 'left_drone'),
            # E.RndPlay(haunted2_wav, 'bass_ooo', rate=settings.out2_rate),
            E.Loop(gs2('haunting')),
            E.Loop(gs2('haunting')),
            # E.Silence(),
            # E.Silence(),
        ]),
        beamz=L.Named('flash_pulse', 0),
    )
