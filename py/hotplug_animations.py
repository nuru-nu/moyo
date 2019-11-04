import numpy as np
import animations as A, colors as C, logic as L, palette as P, signals as S
import settings


ooo_hue = S.SinT(hz=L.Named('ooo_intensity')
                 | S.Lin(shift=0.0025, mult=0.5)) | S.Lin(shift=0.25, mult=0.5)


ooo_color = C.HSV(
    # hue=L.Named("t") | A.Sin(hz=0.2) | S.Lin(shift=0.25, mult=0.5),
    hue=ooo_hue,
    # hue=A.OooHue(),
    value=L.Named("loud"),
)


def get_state_colors(StatePaletteOrStateColorPalette):
    return StatePaletteOrStateColorPalette(
        C.Palette(P.brownish_palette),
        dict(
            brownish_palette=C.Palette(P.brownish_palette),
            coolors_rainbow=C.Palette(P.coolors_rainbow),
            just_greens=C.Palette(P.just_greens),
            blue_purple=C.Palette(P.blue_purple),
            funny_rainbow=C.Palette(P.funny_rainbow),
            # barbie=C.Palette(P.barbie),
            # purple_haze=C.Palette(P.purple_haze),
            red_death=C.Palette(P.red_death),
            gabe_red=C.Palette(P.gabe_red),
            super_red=C.Palette(P.super_red),
            ultra_rainbows=C.Palette(P.ultra_rainbows),
            earth_life=C.Palette(P.earth_life),
        ))


ooo_color = (
    ooo_hue | get_state_colors(C.StateColorPalette)
    | S.Lin(mult=L.Named('loud'))
)


def std():
    return A.Add(*[
        A.GaussianDroplet(
            sigma=(
                L.Named('drone{}'.format(i + 1))
                | S.Lin(shift=0, mult=np.pi / 40)
            ),
            color=C.RGB(1, 0, 0),
            phi=phi,
            r=1,
        ) | C.RedToPalette(C.ColorPalette(P.black_violet))
        for i, phi in enumerate((np.pi / 2, 3 * np.pi / 2))
    ])


def std2():
    colors = get_state_colors(C.StatePalette)
    return A.RPalette(
        shift=L.Named('std2'),
        mult=1,
        palette=colors
    ) | S.Lin(mult=0.2)


def std3():
    colors = get_state_colors(C.StatePalette)
    return A.PhiPalette(
        shift=L.Named('std2'),
        mult=1,
        # mult=S.SinT(hz=.1) | S.Lin(shift=0.75, mult=0.25),
        palette=colors
    ) | S.Lin(mult=0.2)


def test():
    return A.PositionIdentify()


def frozen():
    return A.FullOn(
        color=[0, 0.1, 0],
    )


def into():
    colors = get_state_colors(C.StatePalette)
    return (
        A.RPalette(
            shift=L.Named('std22'),
            mult=-1,
            palette=colors
        ) | S.Lin(mult=L.Named('into') | S.Lin(shift=0.3, mult=0.7))
    )


def ooo():
    return A.FullOn(color=ooo_color)


def flash():
    return (
        A.FullOn(color=C.HSV(
            value=S.SinT(
                hz=L.Named('loud') | S.Lin(shift=0, mult=8)
            ) | S.Lin(shift=0.5, mult=0.5),
            saturation=0,
        ))
    )


def get_data():

    # sphere_arms_by_state = get_sphere_arms_by_state()

    return dict(
        pixels=A.Mixer(dict(
            std=std(),
            std2=std2(),
            std3=std3(),
            test=test(),
            frozen=frozen(),
            into=into(),
            ooo=ooo(),
            flash=flash(),
        )),
    )

    # return dict(
    #     sphere=A.Mixer({
    #         state: sphere_arms[0]
    #         for state, sphere_arms in sphere_arms_by_state.items()
    #     }),
    #     arms=[
    #         A.Mixer({
    #             state: sphere_arms[1](i, arm_config)
    #             for state, sphere_arms in sphere_arms_by_state.items()
    #         })
    #         for i, arm_config in enumerate(settings.arm_configs)
    #     ],
    #     # sphere=get_sphere(),
    #     # arms=[get_arm(arm_config, i)
    #     #       for i, arm_config in enumerate(arm_configs)],
    #     # beamz=L.Named('flash_pulse', 0),
    # )
