

import effects as E


def get_data():
    return dict(
        microphone_effect=E.Compressor(5),
        effector=E.Effector([
            # E.Delay(1) | E.Echo(0.2, 0.9) | E.SigAmp('ios'),
            # E.Echo(0.3, 0.8) | E.SigAmp('iso2'),
            E.Silence(),
            E.Silence(),
            # E.Sinusoidal(50) | E.SigAmp('low'),
            # E.Sinusoidal(400) | E.SigAmp('high'),
            # E.Silence(),
        ]),
        # See `audio.AudioInterface.list_devices()`
        # `None` selects default, `-1` disables.
        input_device=None,
        output_device_1=None,
        output_device_2=-1,
    )
