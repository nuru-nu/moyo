

import effects as E


def get_data():
    return dict(
        effector=E.Effector([
            # E.SigAmp('low'),
            # E.SigAmp('high'),
            E.Passthrough(),
            E.Silence(),
        ]),
        # See `audio.AudioInterface.list_devices()`
        # `None` selects default, `-1` disables.
        input_device=None,
        output_device_1=None,
        output_device_2=-1,
    )
