import importlib

import numpy as np

from smanmi import colors as C, logic as L, palette as P, signals as S
from .. import animations as A, settings


importlib.reload(S)
S.init(settings)
importlib.reload(A)
importlib.reload(C)


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

def phi_red():
    return (
        A.Phi() | S.Lin(L.Named('std2')) | S.Mod(1)
        | C.Palette(P.super_red) | S.Lin(mult=0.2)
    ) + heart()

def std2_bw():
    return (
        A.R() | S.Lin(L.Named('std2')) | S.Mod(1)
        | C.Palette(P.black_white) | S.Lin(mult=0.2)
    )



def std3():
    return (
        A.R() | S.Lin(L.Named('std2')) | S.Mod(1)
        | C.Palette(P.coolors_rainbow) | S.Lin(mult=0.2)
    )


# def std3():
#     colors = get_state_colors(C.StatePalette)
#     return A.PhiPalette(
#         shift=L.Named('std2'),
#         mult=1,
#         # mult=S.Sin(hz=.1) | S.Lin(shift=0.75, mult=0.25),
#         palette=colors
#     ) | S.Lin(mult=0.2)


def identify():
    return A.PositionIdentify()

def test():
    return (
        L.Named('std2_cos2') | A.CompWave(1.8, 2.5)
        | C.Palette(P.quite_bright) | S.Lin(mult=0.5)
    )

def test2():
    return (
        L.Named('std2_cos2') | A.CompWave(1.8, 2.5)
        | C.Palette(P.gabe_red) | S.Lin(mult=0.5)
    )
    # return A.CalibrationPattern()
    # Just for fun : set 3D gradient with sonar sensor...
    return A.Dist3D() | S.Lin(
        mult=L.Named('sonar') | S.Lin(mult=1 / 5),
    ) | C.Palette(P.blue_purple)


heart_palette = P.parse_colors_hex([
    (0, '000'),
    (0.8, 'f00'),
    (1, 'f00'),
])


def heart():
    return (
        A.Dist2D(phi=np.pi/4, r=0) | S.Lin(1, -1) | S.Lin(0, L.Named('heart'))
        | C.Palette(heart_palette)
    ) | S.Lin(mult=0.3)


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

spiral_palette = P.parse_colors_hex([
    (0, '000'),
    (0.4, '000'),
    (0.5, '4f2'),
    (0.6, '000'),
    (1, '000'),
])


def spiral():
    return (A.Spiral(
        dphi=.5/np.pi,
        dr=L.Named('cos2_slow') | S.Lin(0.5, 0.5),
        speed=L.Named('sonar') | S.Lin(mult=8)
    ) | S.Mod(1) | C.Palette(spiral_palette)) + heart()


states = dict(
    std=std(),
    std2=std2(),
    std2_bw=std2_bw(),
    phi_red=phi_red(),
    std3=std3(),
    identify=identify(),
    test=test(),
    test2=test2(),
    heart=heart(),
    frozen=frozen(),
    into=into(),
    ooo=ooo(),
    flash=flash(),
    spiral=spiral(),
)


def css_color_speed():
    return (
        L.Named('std2_cos2') | A.CompWave(1.8, 2.5)
        | C.InterpolPalette(L.Named('valence'), (
            (0, P.gabe_red),
            (.5, P.black_white),
            (1, P.funny_rainbow),
        )) | S.Lin(mult=0.5)
    )


# pixels = A.Mixer(states, default_dt=10)
# pixels = spiral()
pixels = css_color_speed()
