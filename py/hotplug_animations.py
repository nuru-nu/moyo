import numpy as np
import animations as A, logic as L, signals as S
import settings


dg = np.pi / 180


arm_configs = (
    settings.blender_arm_configs if settings.is_blender
    else settings.arm_configs
)

ooo_hue = S.SinT(hz=L.Named('ooo_intensity')
                 | S.Lin(shift=0.05, mult=0.5)) | S.Lin(shift=0.5, mult=0.5)

# https://coolors.co/ffffff-ea7af4-b43e8f-6200b3-8451ad
blueish_palette = A.parse_colors_co_scss('''
$color1: rgba(255, 255, 255, 1);
$color2: rgba(234, 122, 244, 1);
$color3: rgba(180, 62, 143, 1);
$color4: rgba(98, 0, 179, 1);
$color5: rgba(132, 81, 173, 1);''')

# https://coolors.co/7e5920-210f04-dc851f-621b00-f42c04
brownish_palette = A.parse_colors_co_scss('''
$color1: rgba(126, 89, 32, 1);
$color2: rgba(33, 15, 4, 1);
$color3: rgba(220, 133, 31, 1);
$color4: rgba(98, 27, 0, 1);
$color5: rgba(244, 44, 4, 1);''')

ooo_color = A.HSV(
            # hue=L.Named("t") | A.Sin(hz=0.2) | S.Lin(shift=0.5, mult=0.5),
            hue=ooo_hue,
            # hue=A.OooHue(),
            value=L.Named("loud"),
        )
ooo_color = ooo_hue | A.ColorPalette(colors=blueish_palette) | S.Lin(mult=L.Named('loud'))



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
        ooo=A.FullOn(color=ooo_color),
        test=A.ThetaPalette(
            shift=L.Named('ring1'),
            mult=1,
            palette=A.Palette(brownish_palette),
        ),
        # test=A.Add(
        #     A.PhiRing(
        #         width=np.pi / 10,
        #         color=[0.8, 0, 1],
        #         theta=L.Named('ring1') | S.Lin(mult=np.pi),
        #     ),
        #     A.PhiRing(
        #         width=np.pi / 10,
        #         color=[1, 0, 0.8],
        #         theta=L.Named('ring2') | S.Lin(mult=np.pi / 2),
        #     ),
        # ),
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
            color=ooo_color,
            func=lambda x: (1 - x)**2,
        ),
        test=A.ArmPalette(
            arm_config,
            shift=L.Named('ring1'),
            palette=A.Palette(brownish_palette),
        ),
        # test=A.Add(
        #     A.ArmRing(
        #         arm_config,
        #         color=[0.8, 0, 1],
        #         value=(
        #             L.Named('ring1') | S.Lin(shift=-1, mult=2)
        #             | S.Clip() | S.Exp(1.5) | S.Lin(shift=-0.1)
        #         ),
        #         width=0.1,
        #     ),
        #     A.ArmRing(
        #         arm_config,
        #         color=[0.1, 0, 0.8],
        #         value=(
        #             L.Named('ring2') | S.Lin(shift=-1, mult=2)
        #             | S.Clip() | S.Exp(1.5) | S.Lin(shift=-0.1)
        #         ),
        #         width=0.1,
        #     ),
        # ),
        flash=A.ArmGradient(
            arm_config,
            color=A.HSV(
                value=S.SinT(
                    hz=L.Named('loud') | S.Lin(shift=0, mult=8)
                ) | S.Lin(shift=0.5, mult=0.5),
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
