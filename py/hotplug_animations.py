import numpy as np
import animations as A, logic as L, signals as S
import settings


dg = np.pi / 180


arm_configs = (
    settings.blender_arm_configs if settings.is_blender
    else settings.arm_configs
)

ooo_hue = S.SinT(hz=L.Named('ooo_intensity')
                 | S.Lin(shift=0.0025, mult=0.5)) | S.Lin(shift=0.25, mult=0.5)

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

# https://coolors.co/ffffff-cb27ce-8a1a8c-401a8c-000000
white_violet = A.parse_colors_co_scss('''
$color1: rgba(255, 255, 255, 1);
$color2: rgba(203, 39, 206, 1);
$color3: rgba(138, 26, 140, 1);
$color4: rgba(64, 26, 140, 1);
$color5: rgba(0, 0, 0, 1);''')

coolors_rainbow = A.parse_colors_co_scss('''
$color1: rgba(31, 139, 248, 1);
$color2: rgba(237, 37, 78, 1);
$color3: rgba(222, 13, 146, 1);
$color4: rgba(208, 5, 118, 1);
$color5: rgba(249, 220, 92, 1);''')

just_greens = A.parse_colors_co_scss('''
$color1: rgba(56, 108, 11, 1);
$color2: rgba(56, 167, 0, 1);
$color3: rgba(49, 216, 67, 1);
$color4: rgba(4, 106, 56, 1);
$color5: rgba(62, 255, 139, 1);''')

quite_bright = A.parse_colors_co_scss('''
$color1: rgba(48, 69, 41, 1);
$color2: rgba(74, 103, 65, 1);
$color3: rgba(140, 112, 81, 1);
$color4: rgba(237, 180, 88, 1);
$color5: rgba(212, 212, 170, 1);''')

blue_purple = A.parse_colors_co_scss('''
$color1: rgba(202, 44, 146, 1);
$color2: rgba(127, 0, 255, 1);
$color3: rgba(0, 56, 168, 1);
$color4: rgba(129, 20, 83, 1);
$color5: rgba(159, 0, 197, 1);''')

black_violet = A.parse_colors_hex((
    (0, '000'),
    (0.3, '000'),
    (0.6, '418'),
    (1.0, '818'),
))


test_colors = A.parse_colors_hex((
    (0, 'FF0000'),
    (0.1, '000'),
    (0.9, '000'),
    (1.0, '00FF00'),
))

std2_palette = A.Palette(brownish_palette)
std2_palette = A.Palette(blue_purple)
std2_palette = A.Palette(coolors_rainbow)

std3_palette = A.Palette(A.parse_colors_hex((
    (0.0, 'fff'),
    (1.0, '000'),
)))

ooo_color = A.HSV(
    # hue=L.Named("t") | A.Sin(hz=0.2) | S.Lin(shift=0.25, mult=0.5),
    hue=ooo_hue,
    # hue=A.OooHue(),
    value=L.Named("loud"),
)
ooo_color = (
    ooo_hue | A.ColorPalette(colors=brownish_palette)
    | S.Lin(mult=L.Named('loud'))
)


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
    return A.Add(*[
        A.GaussianDroplet(
            sigma=(
                L.Named('drone{}'.format(i + 1))
                | S.Lin(shift=0, mult=np.pi / 40)
            ),
            color=A.RGB(1, 0, 0),
            phi=arm_config.phi,
            theta=np.pi / 2,
        ) | A.RedToPalette(A.ColorPalette(black_violet))
        for i, arm_config in enumerate(settings.arm_configs)
    ])
    # return A.Add(
    #     A.GaussianDroplet(
    #         sigma=L.Named('drone1') | S.Lin(shift=0, mult=np.pi / 40),
    #         color=A.RGB(1, 0, 0),
    #         phi=50 * dg,
    #         theta=np.pi / 2,
    #     ) | A.RedToPalette(A.ColorPalette(black_violet)),
    #     A.GaussianDroplet(
    #         sigma=L.Named('drone2') | S.Lin(shift=0, mult=np.pi / 40),
    #         color=A.RGB(1, 0, 1),
    #         phi=1.3 * np.pi / 2,
    #         theta=np.pi / 2,
    #     ),
    # )


# def get_sphere():
#
#     return A.Mixer(dict(
#         std=stereo_drone_sphere(),
#         std2=A.ThetaPalette(
#             shift=L.Named('std2'),
#             mult=1,
#             # mult=S.SinT(hz=.1) | S.Lin(shift=0.75, mult=0.25),
#             palette=std2_palette,
#         ) | S.Lin(mult=0.5),
#         std3=L.Named('std3') | A.ThetaPaletteWindow(
#             palette=std3_palette,
#             start=0, end=1,
#         ),
#         ooo=A.FullOn(color=ooo_color),
#         # test=A.GaussianDroplet(
#         #     color=A.RGB(1, 1, 1),
#         #     sigma=2 * dg,
#         #     theta=90 * dg,
#         #     phi=0,
#         # ),
#         test=A.ThetaPalette(
#             # shift=L.Named('ring1'),
#             shift=0,
#             mult=1,
#             # palette=A.Palette(brownish_palette),
#             palette=A.Palette(test_colors),
#         ),
#         # test=A.Add(
#         #     A.PhiRing(
#         #         width=np.pi / 10,
#         #         color=[0.8, 0, 1],
#         #         theta=L.Named('ring1') | S.Lin(mult=np.pi),
#         #     ),
#         #     A.PhiRing(
#         #         width=np.pi / 10,
#         #         color=[1, 0, 0.8],
#         #         theta=L.Named('ring2') | S.Lin(mult=np.pi / 2),
#         #     ),
#         # ),
#         flash=A.FullOn(color=A.HSV(
#             value=S.SinT(
#                 hz=L.Named('loud') | S.Lin(shift=0, mult=8)
#             ) | S.Lin(shift=0.5, mult=0.5),
#             saturation=0,
#         )),
#         frozen=A.FullOn(
#             color=[0, 0.1, 0],
#         ),
#     ))


# def get_arm(arm_config, i):
#     return A.Mixer(dict(
#         std=A.ArmGradient(
#             arm_config,
#             color=[1, 0, 1],
#             func=lambda x: (1 - x)**4,
#             # func=lambda x, signals=None: 1*(x < (
#             #     signals.get('right_drone' if i else 'left_drone', 0))),
#             mult=L.Named('right_drone' if i else 'left_drone'),
#         ) | A.RedToPalette(black_violet),
#         std2=A.ArmPalette(
#             arm_config,
#             mult=1,
#             shift=L.Named('std2'),
#             palette=std2_palette,
#         ),  # | A.ArmByDist(arm_config, func=lambda x: 1 - x),
#         std3=L.Named('std3') | A.ArmPaletteWindow(
#             arm_config,
#             palette=std3_palette,
#             start=1, end=1,
#         ),
#         ooo=A.ArmGradient(
#             arm_config,
#             color=ooo_color,
#             func=lambda x: (1 - x)**2,
#         ),
#         test=A.ArmIdentify(arm_config),
#         # test=A.ArmPalette(
#         #     arm_config,
#         #     shift=L.Named('ring1'),
#         #     palette=A.Palette(brownish_palette),
#         # ),
#         # test=A.Add(
#         #     A.ArmRing(
#         #         arm_config,
#         #         color=[0.8, 0, 1],
#         #         value=(
#         #             L.Named('ring1') | S.Lin(shift=-1, mult=2)
#         #             | S.Clip() | S.Exp(1.5) | S.Lin(shift=-0.1)
#         #         ),
#         #         width=0.1,
#         #     ),
#         #     A.ArmRing(
#         #         arm_config,
#         #         color=[0.1, 0, 0.8],
#         #         value=(
#         #             L.Named('ring2') | S.Lin(shift=-1, mult=2)
#         #             | S.Clip() | S.Exp(1.5) | S.Lin(shift=-0.1)
#         #         ),
#         #         width=0.1,
#         #     ),
#         # ),
#         flash=A.ArmGradient(
#             arm_config,
#             color=A.HSV(
#                 value=S.SinT(
#                     hz=L.Named('loud') | S.Lin(shift=0, mult=8)
#                 ) | S.Lin(shift=0.5, mult=0.5),
#                 saturation=0,
#             ),
#         ),
#         frozen=A.ArmFullOn(
#             arm_config,
#             color=[0, 0.1, 0],
#         ),
#     ))


def std():
    return (
        stereo_drone_sphere(),
        lambda i, arm_config: A.ArmGradient(
            arm_config,
            color=[1, 0, 1],
            func=lambda x: (1 - x)**4,
            # func=lambda x, signals=None: 1*(x < (
            #     signals.get('right_drone' if i else 'left_drone', 0))),
            mult=L.Named('drone{}'.format(i + 1)),
        ) | A.RedToPalette(black_violet),
    )


def std2():
    return (
        A.ThetaPalette(
            shift=L.Named('std2'),
            mult=1,
            # mult=S.SinT(hz=.1) | S.Lin(shift=0.75, mult=0.25),
            palette=std2_palette,
        ) | S.Lin(mult=0.5),
        lambda i, arm_config: A.ArmPalette(
            arm_config,
            mult=1,
            shift=L.Named('std2'),
            palette=std2_palette,
        ),
    )


def std3():
    return (
        L.Named('std3') | A.ThetaPaletteWindow(
            palette=std3_palette,
            start=0, end=1,
        ),
        lambda i, arm_config: L.Named('std3') | A.ArmPaletteWindow(
            arm_config,
            palette=std3_palette,
            start=1, end=1,
        )
    )


def ooo():
    return (
        A.FullOn(color=ooo_color),
        lambda i, arm_config: A.ArmGradient(
            arm_config,
            color=ooo_color,
            func=lambda x: (1 - x)**2,
        ),
    )


def test():
    return (
        A.ThetaPalette(
            # shift=L.Named('ring1'),
            shift=0,
            mult=1,
            # palette=A.Palette(brownish_palette),
            palette=A.Palette(test_colors),
        ),
        lambda i, arm_config: A.ArmIdentify(arm_config),
    )


def flash():
    return (
        A.FullOn(color=A.HSV(
            value=S.SinT(
                hz=L.Named('loud') | S.Lin(shift=0, mult=8)
            ) | S.Lin(shift=0.5, mult=0.5),
            saturation=0,
        )),
        lambda i, arm_config: A.ArmGradient(
            arm_config,
            color=A.HSV(
                value=S.SinT(
                    hz=L.Named('loud') | S.Lin(shift=0, mult=8)
                ) | S.Lin(shift=0.5, mult=0.5),
                saturation=0,
            ),
        ),
    )


def frozen():
    return (
        A.FullOn(
            color=[0, 0.1, 0],
        ),
        lambda i, arm_config: A.ArmFullOn(
            arm_config,
            color=[0, 0.1, 0],
        ),
    )


def get_sphere_arms_by_state():
    return dict(
        std=std(),
        std2=std2(),
        std3=std3(),
        ooo=ooo(),
        test=test(),
        flash=flash(),
        frozen=frozen(),
    )


def get_data():

    sphere_arms_by_state = get_sphere_arms_by_state()

    return dict(
        sphere=A.Mixer({
            state: sphere_arms[0]
            for state, sphere_arms in sphere_arms_by_state.items()
        }),
        arms=[
            A.Mixer({
                state: sphere_arms[1](i, arm_config)
                for state, sphere_arms in sphere_arms_by_state.items()
            })
            for i, arm_config in enumerate(arm_configs)
        ],
        # sphere=get_sphere(),
        # arms=[get_arm(arm_config, i)
        #       for i, arm_config in enumerate(arm_configs)],
        # beamz=L.Named('flash_pulse', 0),
    )
