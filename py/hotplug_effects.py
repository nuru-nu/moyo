

import effects as E


def get_data():
    return dict(
        effector=E.Effector([
            # E.SigAmp('low'),
            # E.SigAmp('high'),
            E.Echo(0.1, 0.9),
            E.Echo(0.1, 0.9) | E.Delay(0.5),
            E.Silence(),
            E.Silence(),
        ]),
        # See `audio.AudioInterface.list_devices()`
        input_device=0,
        output_device_1=1,
        output_device_2=None,
    )
