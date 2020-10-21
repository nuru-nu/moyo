import glob
import importlib

import numpy as np
import PIL.Image

from smanmi import colors as C, logic as L, palette as P, signals as S
from .. import animations as A, settings


importlib.reload(S)
S.init(settings)
importlib.reload(A)
importlib.reload(C)
importlib.reload(P)


images = {
    path.split('/')[-1].split('.')[0]: np.array(PIL.Image.open(
        path))[..., :3] / 256
    for path in glob.glob('images/*')
}

ooo_hue = (
    S.Saw(hz=(L.Named('ooo_intensity') | S.Lin(shift=0.0025, mult=0.5)))
    | S.Tocos() | S.Lin(shift=0.25, mult=0.5)
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

animations = dict()


def anim(func):
    animations[func.__name__] = func()


@anim
def fotos():
    return (
        A.R() | S.Lin(L.Named('std2')) | S.Mod(1)
        | C.AllPalettes(L.Named('valence')) | S.Lin(mult=L.Named('arousal'))
    )


@anim
def off():
    # TODO this (and others) return wrong shape !
    return A.Ones() | C.RGB(0, 0, 0)


@anim
def ident():
    return A.PositionIdentify()


@anim
def frozen():
    return A.Ones() | C.RGB(0, .1, 0)


@anim
def drone():
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


@anim
def into():
    return (
        A.R() | S.Lin(L.Named('std2')) | S.Mod(1)
        | state_palette | S.Lin(mult=0.2)
    )


@anim
def wheel():
    return (
        A.Phi() | S.Lin(L.Named('std2')) | S.Mod(1)
        | C.Palette(P.super_red) | S.Lin(mult=0.2)
    )


@anim
def songrad():
    # Just for fun : set 3D gradient with sonar sensor...
    return A.Dist3D() | S.Lin(
        mult=L.Named('sonar') | S.Lin(mult=1 / 5),
    ) | C.Palette(P.coolors_rainbow)


heart_palette = P.parse_colors_hex([
    (0, '000'),
    (0.8, 'f00'),
    (1, 'f00'),
])


@anim
def heart():
    return (
        A.Dist2D(phi=np.pi / 4, r=0) | S.Lin(1, -.2)
        | S.Lin(0, L.Named('heart'))
        | C.Palette(heart_palette)
    ) | S.Lin(mult=0.2)



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
            S.Saw(hz=L.Named('loud') | S.Lin(mult=8))
            | S.Tocos() | S.Lin(shift=0.5, mult=0.5)
        ),
        saturation=0
    )


def laser_spiral(palette, dt):
    return (
        (
            A.Spiral(
                dr=L.Named('valence') | S.Lin(-0.5, 2),
                n=8,
                # aspect=0,#L.Named('valence'),
                # speed=L.Named('arousal') | S.Lin(mult=8)
            )
            + L.Named('saw_a') + L.Constant(dt)
        ) | S.Mod(1) | C.Palette(palette)
    )


@anim
def laser():
    return (
        laser_spiral(P.peak_blue, 0)
        + laser_spiral(P.peak_green, 0.5)
    )


@anim
def spiral():
    return (
        (
            A.Spiral(
                dr=L.Named('valence') | S.Lin(1, 2),
                n=4,
            )
            + (L.Named('saw_a') | S.Lin(0, 2))
        ) | S.Mod(1) | C.Palette(P.peak_green)
    )


@anim
def aliasing():
    return A.Aliasing(
    ) | S.Mod(1) | C.Palette(P.peak_blue)


@anim
def cwave():
    return (
        L.Named('std2') | S.Lin(0, 2) | S.Tocos() | A.CompWave(1.8, 2.5)
        | C.InterpolPalette(L.Named('valence'), (
            (0, P.black_violet),
            #(.5, P.black_white),
            (1, P.coolors_rainbow),
        )) | S.Lin(mult=L.Named('arousal')) | S.Lin(0, 0.5)
    )


@anim
def stripes():
    return (
        (
            A.PhiRXY(dg=L.Named('valence') | S.Lin(0, 90))
            | S.T() | S.ElementAt(0)
            | S.Lin(0, 2)
        ) + (
            L.Named('saw_a') | S.Lin(0, 2)
        )
    ) | S.Mod(1) | C.Palette(P.funny_rainbow)


@anim
def noise():
    return A.NoiseCycle(
        hz=L.Named('arousal') | S.To(0, 3),
    ) | C.InterpolPalette(L.Named('valence'), (
        (0, P.brownish_palette),
        (1, P.black_violet),
        # (1, P.black_white),
        # (1, P.ultra_rainbows),
    )) | S.To(0, 0.6)  #| S.Lin(mult=L.Named('valence')) | S.Lin(0, 0.5)


@anim
def img():
    return A.Proj(
        images['autumn_forest'],
        scale=L.Named('arousal'),
        rotate=L.Named('valence') | S.To(-180, 180),
        dx=L.Named('std2_cos2') | S.To(-.01, .01),
    ) | S.To(0, .3)


def make_image(image):
    return A.Proj(
        image,
        # scale=1,
        scale=L.Named('arousal') | S.To(0.1, 1),
        # dy=L.Named('arousal') | S.To(.5, -.5),
        # dx=L.Named('valence') | S.To(-.5, .5),
        # rotate=L.Named('valence') | S.To(-180, 180),
        rotate=L.Named('t'),
        # dx=L.Named('std2_cos2') | S.To(-.01, .01),
    ) | S.To(0, .3)


animations.update({
    f'p_{name}': make_image(image) for name, image in images.items()
})


pixels = A.ActionMixer(animations)
