
import scipy

import effects as E, settings, util


def get_sample(name):
    sr, wav = scipy.io.wavfile.read(
         '../data/samples/{}_16.wav'.format(name))
    assert sr == settings.rate
    return util.int16_to_float(wav)

def get_data():
    haunted_wav = get_sample('haunting-ambience_D_major')
    return dict(
        microphone_effect=E.Compressor(10),
        effector=E.Effector([
            # E.Delay(1) | E.Echo(0.2, 0.9) | E.SigAmp('ios'),
            # E.Echo(0.3, 0.8) | E.SigAmp('iso2'),
            # E.Silence(),
            # E.Silence(),
            # E.Sinusoidal(50) | E.SigAmp('low'),
            # E.Sinusoidal(400) | E.SigAmp('high'),
            # E.Silence(),
            E.RndSub(
                haunted_wav,
                sample_minmax=[3, 8],
                break_minmax=[1, 20],
                ramp_minmax=[2, 4]),
            E.RndSub(
                haunted_wav,
                sample_minmax=[3, 8],
                break_minmax=[1, 20],
                ramp_minmax=[2, 4]),
        ]),
        # See `audio.AudioInterface.list_devices()`
        # `None` selects default, `-1` disables.
        input_device=None,
        output_device_1=None,
        output_device_2=-1,
    )
