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


funny_rainbow = A.parse_colors_co_scss('''
$color1: rgba(249, 200, 14, 1);
$color2: rgba(248, 102, 36, 1);
$color3: rgba(234, 53, 70, 1);
$color4: rgba(102, 46, 155, 1);
$color5: rgba(67, 188, 205, 1);''')

barbie = A.parse_colors_co_scss('''
$color1: rgba(247, 237, 240, 1);
$color2: rgba(244, 203, 198, 1);
$color3: rgba(244, 175, 171, 1);
$color4: rgba(244, 238, 169, 1);
$color5: rgba(244, 244, 130, 1);''')

purple_haze = A.parse_colors_co_scss('''
$color1: rgba(110, 68, 255, 1);
$color2: rgba(184, 146, 255, 1);
$color3: rgba(244, 175, 171, 1);
$color4: rgba(255, 194, 226, 1);
$color5: rgba(239, 122, 133, 1);''')

red_death = A.parse_colors_co_scss('''
$color1: rgba(252, 68, 15, 1);
$color2: rgba(162, 0, 33, 1);
$color3: rgba(245, 47, 87, 1);
$color4: rgba(247, 157, 92, 1);
$color5: rgba(237, 237, 244, 1);''')

gabe_red = A.parse_colors_co_scss('''
$color1: rgba(88, 39, 7, 1);
$color2: rgba(162, 0, 33, 1);
$color3: rgba(255, 75, 62, 1);
$color4: rgba(255, 178, 15, 1);
$color5: rgba(255, 229, 72, 1);''')

super_red = A.parse_colors_co_scss('''
$color1: rgba(196, 30, 61, 1);
$color2: rgba(125, 17, 40, 1);
$color3: rgba(255, 44, 85, 1);
$color4: rgba(60, 9, 25, 1);
$color5: rgba(226, 41, 79, 1);''')

ultra_rainbows = A.parse_colors_co_scss('''
$color1: rgba(4, 231, 98, 1);
$color2: rgba(245, 183, 0, 1);
$color3: rgba(255, 44, 85, 1);
$color4: rgba(0, 161, 228, 1);
$color5: rgba(137, 252, 0, 1);''')

earth_life = A.parse_colors_co_scss('''
$color1: rgba(79, 52, 90, 1);
$color2: rgba(89, 60, 143, 1);
$color3: rgba(143, 169, 152, 1);
$color4: rgba(156, 191, 167, 1);
$color5: rgba(201, 242, 153, 1);''')

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
# std2_palette = A.Palette(blue_purple)
# std2_palette = A.Palette(coolors_rainbow)

std4_palette = A.Palette(blue_purple)

ooo_color = A.HSV(
    # hue=L.Named("t") | A.Sin(hz=0.2) | S.Lin(shift=0.25, mult=0.5),
    hue=ooo_hue,
    # hue=A.OooHue(),
    value=L.Named("loud"),
)


def get_state_colors(StatePaletteOrStateColorPalette):
    return StatePaletteOrStateColorPalette(
        A.Palette(brownish_palette),
        dict(
            brownish_palette=A.Palette(brownish_palette),
            coolors_rainbow=A.Palette(coolors_rainbow),
            just_greens=A.Palette(just_greens),
            blue_purple=A.Palette(blue_purple),
            funny_rainbow=A.Palette(funny_rainbow),
            # barbie=A.Palette(barbie),
            # purple_haze=A.Palette(purple_haze),
            red_death=A.Palette(red_death),
            gabe_red=A.Palette(gabe_red),
            super_red=A.Palette(super_red),
            ultra_rainbows=A.Palette(ultra_rainbows),
            earth_life=A.Palette(earth_life),
        ))


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


ooo_color = (
    ooo_hue | get_state_colors(A.StateColorPalette)
    | S.Lin(mult=L.Named('loud'))
)


def stereo_drone_sphere():
    return A.Add(*[
        A.GaussianDroplet(
            sigma=(
                L.Named('drone{}'.format(i + 1))
                | S.Lin(shift=0, mult=np.pi / 40)
            ),
            color=A.RGB(1, 0, 0),
            phi=phi,
            theta=np.pi / 2,
        ) | A.RedToPalette(A.ColorPalette(black_violet))
        for i, phi in [(0, np.pi / 2), (1, 3 * np.pi / 2)]
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


def std():
    return (
        stereo_drone_sphere(),
        lambda i, arm_config: A.ArmGradient(
            arm_config,
            color=[1, 0, 1],
            func=lambda x: (1 - x + 0.3)**4,
            # func=lambda x, signals=None: 1*(x < (
            #     signals.get('right_drone' if i else 'left_drone', 0))),
            mult=L.Named(
                ['drone1', 'drone2',
                 'drone1', 'drone2', 'drone2',
                 'drone3'][i]
            ),
        ) | A.RedToPalette(black_violet),
    )


def std2():
    colors = get_state_colors(A.StatePalette)
    return (
        A.ThetaPalette(
            shift=L.Named('std2'),
            mult=1,
            # mult=S.SinT(hz=.1) | S.Lin(shift=0.75, mult=0.25),
            palette=colors
        ) | S.Lin(mult=0.2),
        lambda i, arm_config: A.ArmPalette(
            arm_config,
            mult=1,
            shift=L.Named('std2'),
            palette=colors,
        ),
    )


def std3():
    colors = A.parse_colors_hex((
        (0.0, 'fff'),
        (1.0, '000'),
    ))
    colors = blue_purple
    sig = 'ring1'

    return (
        A.PhiPalette(
            shift=L.Named(sig),
            mult=1,
            # mult=S.SinT(hz=.1) | S.Lin(shift=0.75, mult=0.25),
            palette=A.Palette(colors),
        ) | S.Lin(mult=0.5),
        lambda i, arm_config: A.ArmFullOn(
            arm_config,
            color=(
                L.Named(sig) | S.Lin(shift=arm_config.phi, mod=2 * np.pi)
                | A.ColorPalette(colors)
            ),
        ),
    )


def std4():
    return (
        L.Named('std3') | A.ThetaPaletteWindow(
            palette=std4_palette,
            start=0, end=1,
        ),
        lambda i, arm_config: L.Named('std3') | A.ArmPaletteWindow(
            arm_config,
            palette=std4_palette,
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
        A.GaussianDroplet(
            sigma=np.pi / 40,
            color=A.RGB(1, 0, 0),
            phi=82 * dg,
            theta=np.pi / 2,
        ) | A.RedToPalette(A.ColorPalette(black_violet)),
        # A.ThetaPalette(
        #     # shift=L.Named('ring1'),
        #     shift=0,
        #     mult=1,
        #     # palette=A.Palette(brownish_palette),
        #     palette=A.Palette(test_colors),
        # ),
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


def into():
    colors = get_state_colors(A.StatePalette)
    return (
        A.ThetaPalette(
            shift=L.Named('std22'),
            mult=-1,
            # mult=S.SinT(hz=.1) | S.Lin(shift=0.75, mult=0.25),
            palette=colors
        ) | S.Lin(mult=L.Named('into') | S.Lin(shift=0.3, mult=0.7)),
        lambda i, arm_config: A.ArmPalette(
            arm_config,
            mult=-1,
            shift=L.Named('std2'),
            palette=colors,
        ) | A.ArmByDist(arm_config, func=lambda x: (1 - x)**2.5),
    )


def get_sphere_arms_by_state():
    return dict(
        std=std(),
        std2=std2(),
        std3=std3(),
        std4=std4(),
        ooo=ooo(),
        test=test(),
        flash=flash(),
        frozen=frozen(),
        into=into(),
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
            for i, arm_config in enumerate(settings.arm_configs)
        ],
        # sphere=get_sphere(),
        # arms=[get_arm(arm_config, i)
        #       for i, arm_config in enumerate(arm_configs)],
        # beamz=L.Named('flash_pulse', 0),
    )
