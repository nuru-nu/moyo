import importlib

import numpy as np

from smanmi import colors as C, logic as L, palette as P, signals as S
from .. import animations as A, settings


importlib.reload(S)
S.init(settings)
importlib.reload(A)


ooo_hue = (
    S.Sin(hz=L.Named('ooo_intensity') | S.Lin(shift=0.0025, mult=0.5))
    | S.Lin(shift=0.25, mult=0.5)
)


state_palette = S.Apply(C.StatePalette(
    P.brownish_palette,
    dict(
        brownish_palette=P.brownish_palette,
        coolors_rainbow=P.coolors_rainbow,
        just_greens=P.just_greens,
        blue_purple=P.blue_purple,
        funny_rainbow=P.funny_rainbow,
        # barbie=P.barbie,
        # purple_haze=P.purple_haze,
        red_death=P.red_death,
        gabe_red=P.gabe_red,
        super_red=P.super_red,
        ultra_rainbows=P.ultra_rainbows,
        earth_life=P.earth_life,
    )))


def std():
    return A.add([
        A.GaussianDroplet(
            sigma=(
                L.Named('drone{}'.format(i + 1))
                | S.Lin(shift=0, mult=np.pi / 40)
            ),
            phi=phi,
            r=1,
        ) | C.Palette(P.black_violet)
        for i, phi in enumerate((np.pi / 2, 3 * np.pi / 2))
    ])


def std2():
    return (
        A.R() | S.Lin(L.Named('std2')) | S.Mod(1)
        | state_palette | S.Lin(mult=0.2)
    )


# def std3():
#     colors = get_state_colors(C.StatePalette)
#     return A.PhiPalette(
#         shift=L.Named('std2'),
#         mult=1,
#         # mult=S.Sin(hz=.1) | S.Lin(shift=0.75, mult=0.25),
#         palette=colors
#     ) | S.Lin(mult=0.2)


def test():
    return (
        L.Named('std2') | A.CompWave(1.8, 2.5)
        | C.Palette(P.funny_rainbow)
    )
    # return A.CalibrationPattern()
    # Just for fun : set 3D gradient with sonar sensor...
    return A.Dist3D() | S.Lin(
        mult=L.Named('sonar') | S.Lin(mult=1 / 5),
    ) | C.Palette(P.blue_purple)
    return A.PositionIdentify()


heart_palette = P.parse_colors_hex([
    (0, '000'),
    (0.8, 'f00'),
    (1, 'f00'),
])


def test2():
    return (
        A.Dist2D(phi=0, r=1) | S.Lin(1, -1) | S.Lin(0, L.Named('heart'))
        | C.Palette(heart_palette)
    )


def frozen():
    return A.Ones() | C.RGB(0, .1, 0)


def into():
    return (
        A.R() | S.Lin(L.Named('std22'), -1) | S.Mod(1)
        | state_palette
        | S.Lin(mult=L.Named('into')) | S.Lin(shift=0.3, mult=0.7)
    )


def ooo():
    return (
        A.Ones() | S.Lin(mult=L.Named('loud'))
    ) * (
        ooo_hue | state_palette
    )


def flash():
    return A.Ones() * C.HSV(
        value=(
            S.Sin(hz=L.Named('loud') | S.Lin(mult=8))
            | S.Lin(shift=0.5, mult=0.5)
        ),
        saturation=0
    )


states = dict(
    std=std(),
    std2=std2(),
    test=test(),
    test2=test2(),
    frozen=frozen(),
    into=into(),
    ooo=ooo(),
    flash=flash(),
)


pixels = A.Mixer(states)
