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
N = L.N


images = {
    path.split('/')[-1].split('.')[0]: np.array(PIL.Image.open(
        path))[..., :3] / 256
    for path in sorted(glob.glob('images/*'))
    if path.split('.')[-1].lower() in ('jpg', 'jpeg', 'png')
}
ncas = {
    path.split('/')[-1].split('.')[0]: np.load(path, allow_pickle=True)
    for path in sorted(glob.glob('images/*.npy'))
}

palettes = {
    name: value
    for name, value in P.__dict__.items()
    if P.is_palette(value) and not name.startswith('_')
}

ooo_hue = (
    S.Saw(hz=(L.Named('ooo_intensity') | S.Lin(shift=0.0025, mult=0.5)))
    | S.Tocos() | S.Lin(shift=0.25, mult=0.5)
)

state_palette = S.Apply(P.StatePalette(P.brownish, palettes))
palette = S.Apply(P.NamedPalette(L.Named('palette')))

animations = dict()


def anim(func):
    animations[func.__name__] = func()
    return func


heart_palette = P.parse_colors_hex([
    (0, '000'),
    (0.8, 'f00'),
    (1, 'f00'),
])


@anim
def heart():
    return (
        A.Dist2D(phi=np.pi / 4, r=0) | S.Lin(1, -.5)
        | S.Lin(0, L.Named('heart'))
        | P.Palette(heart_palette)
    ) | S.Lin(mult=0.2)


@anim
def flash():
    x = S.Const(10) | S.Int(mod=1) | S.Tocos()
    return A.FullOn(C.RGB(x, x, x))

@anim
def test():
    return A.FullOn(C.RGB(1, 1, 1)) | A.GaussianActivation(
        min=0.05, std=N.rnd1 | S.To(0.5, 1.5))


def R():
    return (
        A.R() | S.Lin(
            L.Named('v0') | S.To(0, 3) | S.Int(mod=1)
        ) | S.Mod(1)
        | palette
    )


def Renv(sig):
    return R() * S.Const(0.4) * (
        A.R() | S.Norm() | S.F(
            S.gauss_std,
            sig
        )
    )


@anim
def Rr():
    return Renv(
        L.Named('rnd1') | S.To(0.5, 1.2),
    )


@anim
def Rc():
    return Renv(
        L.Named('closest') | S.To(0.2, 1.2),
    ) + heart()


@anim
def R2():
    return (
        A.R() | S.Lin(
            L.Named('v0') | S.To(0, 3) | S.Int(mod=1)
        ) | S.Mod(1)
        | palette
    ) | A.GaussianActivation(min=0.1, std=0.5)


@anim
def off():
    return A.FullOn(C.RGB(0, 0, 0))


@anim
def ident():
    return A.PositionIdentify()


@anim
def frozen():
    return A.FullOn(C.RGB(0, .15, 0))


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
        ) | P.Palette(P.black_violet)
        for i, phi in enumerate((np.pi / 2, 3 * np.pi / 2))
    ])


# def into():
#     return (
#         A.R() | S.Lin(L.Named('std22'), -1) | S.Mod(1)
#         | state_palette
#         | S.Lin(mult=L.Named('into')) | S.Lin(shift=0.3, mult=0.7)
#     )


@anim
def into():
    return (
        A.R() | S.Lin(L.Named('std2')) | S.Mod(1)
        | state_palette | S.Lin(mult=0.2)
    )


@anim
def wheel():
    return (
        A.Phi() | S.Lin(L.Named('v0') | S.Int(mod=1)) | S.Mod(1)
        | state_palette | S.Lin(mult=0.2)
    )


@anim
def songrad():
    # Just for fun : set 3D gradient with sonar sensor...
    return A.Dist3D() | S.Lin(
        mult=L.Named('sonar') | S.Lin(mult=1 / 5),
    ) | P.Palette(P.coolors_rainbow)


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
            + L.Named('saw_a') + S.Const(dt)
        ) | S.Mod(1) | P.Palette(palette)
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
            + (L.Named('closest') | S.To(-2, 2) | S.Int(mod=1))
            # + (L.Named('saw_a') | S.Lin(0, 2))
        ) | S.Mod(1) | P.Palette(P.peak_green)
    )


@anim
def aliasing():
    return A.Aliasing(
    ) | S.Mod(1) | P.Palette(P.peak_blue) | A.RGauss(L.Named('arousal') | S.To(0, 4))


@anim
def cwave():
    return (
        L.Named('std2') | S.Lin(0, 2) | S.Tocos() | A.CompWave(1.8, 2.5)
        | P.InterpolPalette(L.Named('valence'), (
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
    ) | S.Mod(1) | P.Palette(P.funny_rainbow)


@anim
def noise():
    return A.NoiseCycle(
        # hz=L.Named('arousal') | S.To(0, 3),
        hz=0.2,
    # ) | (palette
    # ) | (P.Palette(P.peak_green)
    ) | P.InterpolPalette(L.Named('valence'), (
        (0, P.peak_green),
        (0.5, P.peak_blue),
        (1, P.peak_vio),
    )
    #     (0, P.brownish),
    #     (1, P.black_violet),
        # (1, P.black_white),
        # (1, P.ultra_rainbows),
    ) | S.To(0, 0.8) | A.RGauss(2)  #| S.Lin(mult=L.Named('valence')) | S.Lin(0, 0.5)


@anim
def img():
    return A.Proj(
        S.Dict(L.Named('image'), images),
        scale=L.Named('v0') | S.To(0, 2),
        rotate=L.Named('v1') | S.To(-180, 180),
    ) | S.To(0, L.Named('v2'))


@anim
def nca():
    return A.NCA2D(
        data=S.Dict(N.nca, ncas),
        mapping=A.xy_mapping,
    )

@anim
def charge():
    # Abelton charging sound
    # 1. growing brighter
    # 2. turning faster
    # 3. inside out aditional layers (keep brightest superpos)
    rot1 = L.Named('charge') | S.To(0, 100) | S.Int(mod=360)
    rot2 = L.Named('charge') | S.To(0, 120) | S.Int(mod=360)
    anim1 = A.Proj(images['supernova1'], scale=9.0, rotate=rot1)
    anim1 = anim1 | S.To(0, L.Named('charge') | S.To(0.8, 1))
    anim2 = A.Proj(images['covid_nmn'], scale=0.6, rotate=rot2)
    anim2 = anim2 | S.To(0, L.Named('charge') | S.From(0.5, 1) | S.To(0, 0.8) | S.Clip())
    return A.Sum(anim1, anim2) + heart()

@anim
def rotimg():
    return A.Proj(
        S.Dict(L.Named('image'), images),
        scale=L.Named('v0') | S.To(0, 10),#  | S.Int(mod=2) | S.Tocos() | S.To(1, 1.5),
        rotate=L.Named('v1') | S.To(0, 50) | S.Int(mod=360),
    ) | S.To(0, L.Named('v2'))


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


# animations.update({
#     f'p_{name}': make_image(image) for name, image in images.items()
# })


@anim
def S1():
    return noise() + heart()

@anim
def S3():
    return (
        (A.R() + (S.Const(1) | S.Int(mod=1))) | S.Mod(1)
        | P.InterpolPalette(L.Named('valence'), (
            (0, P.white_violet),
            (1, P.ultra_rainbows),
        ))
        # | palette
        | S.Lin(mult=L.Named('arousal'))
    ) * (L.Named('arousal') | S.To(0.2, 1))

pixels = A.Mixer(animations)
