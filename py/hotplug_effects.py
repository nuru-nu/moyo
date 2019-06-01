
import scipy

import effects as E, settings, util


_get_sample_cache = {}
def get_sample(name, rate):
    global _get_sample_cache
    key = '{} {}'.format(name, rate)
    if not key in _get_sample_cache:
        sr, wav = scipy.io.wavfile.read(
            '../data/samples/{}/{}.wav'.format(rate, name))
        assert sr == rate
        _get_sample_cache[key] = util.int16_to_float(wav)
    return _get_sample_cache[key]


def get_data():
    haunted1_wav = get_sample('haunting-ambience_D_major',
                              rate=settings.out1_rate)
    dark1_wav = get_sample('haunting-ambience_D_major',
                           rate=settings.out1_rate)
    haunted2_wav = get_sample('haunting-ambience_D_major',
                              rate=settings.out2_rate)
    dark2_wav = get_sample('dark-soundscape_138bpm_F_minor',
                           rate=settings.out2_rate)
    return dict(
        effector1=E.Effector([
            # E.Delay(1) | E.Echo(0.2, 0.9) | E.SigAmp('ios'),
            # E.Echo(0.3, 0.8) | E.SigAmp('iso2'),
            # E.SilenceOrPlaying(),
            E.RndPlay(dark1_wav, 'right_drone'),
            E.RndPlay(dark1_wav, 'left_drone'),
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
        effector2=E.Effector([
            E.RndPlay(haunted2_wav, 'right_drone'),
            E.Silence(),
            # E.RndPlay(haunted2_wav, 'left_drone'),
            # E.RndPlay(haunted2_wav, 'bass_ooo', rate=settings.out2_rate),
            # E.Silence(),
        ]),
    )
