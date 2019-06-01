import numpy as np
import animations as A, logic as L, signals as S
import settings


dg = np.pi / 180


arm_configs = (
    settings.blender_arm_configs if settings.is_blender
    else settings.arm_configs
)

ooo_hue = S.SinT(hz=L.Named('ooo_intensity')
                 | S.Lin(shift=0.1, mult=1)) | S.Lin(shift=0.5, mult=0.5)


def two_rings():
    return A.Add(
        A.PhiRing(
            theta=S.SinT(hz=0.1) | S.Lin(shift=-2, mult=np.pi / 4),
            width=0.3,
            color=A.RGB(1, 0, 0),
        ),
        A.PhiRing(
            theta=A.SinT(hz=0.2) | S.Lin(shift=-2, mult=np.pi / 4),
            width=0.3,
            color=A.RGB(0, 0, 1),
        ),
    )


def stereo_drone_sphere():
    return A.Add(
        A.GaussianDroplet(
            sigma=L.Named('left_drone') | S.Lin(shift=0, mult=np.pi / 40),
            color=A.RGB(1, 0, 1),
            phi=0,
            theta=np.pi / 2,
        ),
        A.GaussianDroplet(
            sigma=L.Named('right_drone') | S.Lin(shift=0, mult=np.pi / 40),
            color=A.RGB(1, 0, 1),
            phi=1.3 * np.pi / 2,
            theta=np.pi / 2,
        ),
    )


def get_sphere():

    return A.Mixer(dict(
        std=stereo_drone_sphere(),
        ooo=A.FullOn(color=A.HSV(
            # hue=L.Named("t") | A.Sin(hz=0.2) | S.Lin(shift=0.5, mult=0.5),
            hue=ooo_hue,
            # hue=A.OooHue(),
            value=L.Named("loud"),
        )),
        test=A.Add(
            A.PhiRing(
                width=np.pi / 10,
                color=[0.8, 0, 1],
                theta=L.Named('ring1') | S.Lin(mult=np.pi),
            ),
            A.PhiRing(
                width=np.pi / 10,
                color=[1, 0, 0.8],
                theta=L.Named('ring2') | S.Lin(mult=np.pi / 2),
            ),
        ),
        flash=A.FullOn(color=A.HSV(
            value=S.SinT(
                hz=L.Named('loud') | S.Lin(shift=0, mult=8)
            ) | S.Lin(shift=0.5, mult=0.5),
            saturation=0,
        )),
    ))


def get_arm(arm_config, i):
    return A.Mixer(dict(
        std=A.ArmGradient(
            arm_config,
            color=[1, 0, 1],
            func=lambda x: (1 - x)**4,
            # func=lambda x, signals=None: 1*(x < (
            #     signals.get('right_drone' if i else 'left_drone', 0))),
            mult=L.Named('right_drone' if i else 'left_drone'),
        ),

        ooo=A.ArmGradient(
            arm_config,
            color=A.HSV(
                # hue=S.SinT(hz=0.2) | S.Lin(shift=0.5, mult=0.5),
                # hue=A.OooHue(),
                hue=ooo_hue,
                value=L.Named("loud"),
            ),
            func=lambda x: (1 - x)**2,
        ),
        test=A.Add(
            A.ArmRing(
                arm_config,
                color=[0.8, 0, 1],
                value=(
                    L.Named('ring1') | S.Lin(shift=-1, mult=2)
                    | S.Clip() | S.Exp(1.5) | S.Lin(shift=-0.1)
                ),
                width=0.1,
            ),
            A.ArmRing(
                arm_config,
                color=[0.1, 0, 0.8],
                value=(
                    L.Named('ring2') | S.Lin(shift=-1, mult=2)
                    | S.Clip() | S.Exp(1.5) | S.Lin(shift=-0.1)
                ),
                width=0.1,
            ),
        ),
        flash=A.ArmGradient(
            arm_config,
            color=A.HSV(
                value=S.SinT(hz=4) | S.Lin(shift=0.5, mult=0.5),
                saturation=0,
            ),
        ),
    ))


def get_data():

    return dict(
        sphere=get_sphere(),
        arms=[get_arm(arm_config, i)
              for i, arm_config in enumerate(arm_configs)]
    )
