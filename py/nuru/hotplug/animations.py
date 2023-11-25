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

blue = P.parse_colors_hex([
    (0, '000'),
    (1, '00f'),
])

orange = P.parse_colors_hex([
    (0, '000'),
    (1, 'f80'),
])

red = P.parse_colors_hex([
    (0, '000'),
    (1, 'f00'),
])


@anim
def radial_wave():
    return (
        L.Named('connection') | S.Lin(0.02, 0.2) | A.SinWave(3) | P.InterpolPalette(
            L.Named('connection'), 
            (
                (0, P.blueish),
                (1, P.gabe_red),
            )
        )
    )

@anim
def speaking_radial_wave():
    return (
        L.Named('arousal') | S.Lin(-0.1, -0.4) | A.SinWave(3) | P.InterpolPalette(
            L.Named('connection'), 
            (
                (0, P.blueish),
                (1, P.gabe_red),
            )
        )
    )

@anim
def radial_pulse():
    return L.Named('rnd1') * S.Const(2) + S.Const(1) | S.Int() | S.Tocos() | P.Palette(orange) | A.RGauss(1)

@anim
def radial_annoyance():
    return L.Named('annoyance_build_up') | P.Palette(heart_palette) | A.RGauss(3)

@anim
def blue_standing_wave():
    return (
        L.Named('t') | S.Lin(mult=0.8) | A.SandingWave(3) | P.Palette(P.blueish)
    )

@anim
def red_standing_wave():
    return (
        L.Named('t') | S.Lin(mult=2) | A.SandingWave(3) | P.Palette(P.gabe_red)
    )

@anim
def heart():
    return (
        A.Dist2D(phi=np.pi / 4, r=0) | S.Lin(1, -.5)
        | S.Lin(0, N.heart)
        # | S.Lin(0, N.heart_a)
        | P.Palette(heart_palette)
    ) | S.Lin(mult=0.2)

@anim
def heart2():
    inp = N.v1
    inp = N.heart
    return A.FullOn(
        (N.rnd1 | palette) * inp
        # (N.heart | palette) * N.heart
    ) * (
        A.Dist2D(0, 0) | S.From(0, 5) | S.To(1, 0) | S.To(
            0.0,
            inp | S.To(0.5, 1)
        )
    # ) * (
    #     A.Dist2D(phi=np.pi / 4, r=0) | S.From(-1, 0)
    #     | S.To(0, L.Named('heart'))
    #     # | P.Palette(heart_palette)
    ) | S.To(0, N.v0)


@anim
def flash():
    x = S.Const(10) | S.Int(mod=1) | S.Tocos()
    return A.FullOn(C.RGB(x, x, x))


@anim
def R():
    return (
        A.R() | S.Lin(
            L.Named('v0') | S.To(-2, 2) | S.Int(mod=1)
        ) | S.Mod(1)
        | palette
    )


def Renv(sig, value=0.4):
    return R() * S.Const(value) * (
        A.R() | S.Norm() | S.F(
            S.gauss_std,
            sig
        )
    )


@anim
def Rr():
    return Renv(
        L.Named('rnd1') | S.To(0.5, 1.2),
        value=N.v1,
    )


@anim
def Rc():
    return Renv(
        L.Named('closest') | S.To(0.2, 1.2),
    )


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
        A.Phi() | S.From(0, 2*np.pi) | S.Lin(N.v1 | S.Int(mod=1)) | S.Mod(1)
        | palette | S.Lin(mult=N.v0)
    )


@anim
def white():
    return A.FullOn(C.RGB(1, 1, 1))


@anim
def rnd():
    return A.FullOn(N.rnd1 | palette) | S.To(0, N.v0)


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
        )) | S.Lin(mult=L.Named('arousal')) | S.Lin(0, 1)
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
def charge():
    # Abelton charging sound
    # 1. growing brighter
    # 2. turning faster
    # 3. inside out aditional layers (keep brightest superpos)
    ctrl = N.charge
    # ctrl = N.v0
    rot1 = ctrl | S.To(0, 100) | S.Int(mod=360)
    rot2 = ctrl | S.To(0, 120) | S.Int(mod=360)
    anim1 = A.Proj(images['supernova1'], scale=9.0, rotate=rot1)
    # anim1 = anim1  | A.GaussianActivation
    anim1 = anim1 | S.To(0.2, ctrl | S.To(0.8, 1))
    anim2 = A.Proj(images['covid_nmn'], scale=0.6, rotate=rot2)
    anim2 = anim2 | S.To(0, ctrl | S.From(0.5, 1) | S.To(0, 0.8) | S.Clip())
    return A.Sum(anim1, anim2)

@anim
def hi():
    return (
        A.R() | S.Lin(S.Const(-1) | S.Int(mod=1)) | S.Mod(1)
        | P.Palette(P.ultra_rainbows)
    )

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
    return noise()

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


@anim
def nca():
    # TODO investigate why swirly_0063 gets so pink after ~ minutes
    # TODO e.g. flip direction in mapping
    return A.NCA2D(
        data=N.nca,
        speed=N.nca_speed,
        clip=N.nca_clip,
        wrapx=N.nca_wrap,
        # width=256, height=256,
        dydt=N.anim_into | S.To(0, 20),
    )

@anim
def nca2():
    return A.NCA2D(
        data=N.nca2,
        speed=N.nca_speed2,
        clip=N.nca_clip2,
        wrapx=N.nca_wrap2,
        # width=256, height=256,
        dydt=N.anim_into | S.To(0, 20),
    )


@anim
def sleep2():
    return A.NCA2D(
        data='fibrous_0132',
        clip=True,
        speed=0.8,
        wrapx=True,
    ) | A.RGauss(N.rnd1 | S.To(2, 5)
    ) | S.To(0, N.v0)


@anim
def sleep():
    return (A.NCA2D(
        data='scaly_0147',
        clip=True,
        speed=1.44,
        wrapx=True,
    ) | S.To(0, 0.23) | A.Overwrite(heart() * S.Const(.3), 50))


@anim
def wakeup2():
    ctrl = N.wakeup
    ctrl = N.v0  # for testing
    return A.NCA2D(
        # data='fibrous_0132',
        data='frilly_0006',  # For illustration purposes something funky.
        clip=True,
        speed=ctrl | S.To(0.8, 3),
        wrapx=True,
    ) | A.RGauss(
        ctrl | S.To(N.rnd1 | S.To(2, 5), 15)
    ) | S.To(0, ctrl | S.To(.3, .6))


@anim
def wakeup():
    ctrl = N.wakeup
    ctrl = N.v0
    return ((
        A.R() | S.Lin(
            ctrl | S.To(-.7, -1) | S.Int(mod=1)
        ) | S.Mod(1)
        | palette
    # ) * (
    #     A.NCA2D(
    #         # data='stratified_0115',  # For illustration purposes something funky.
    #         data='frilly_0093',  # For illustration purposes something funky.
    #         clip=True,
    #         speed=8,
    #         wrapx=True,
    #     ) | S.To(.5, 1.5)
    ) | A.RGauss(ctrl | S.To(2, 7)) | S.To (0, 0.5) 
      | A.Overwrite(heart() * S.Const(.7), 20))


# @anim
# def awake():
#     ctrl = N.v0  # for testing
#     return ((A.NCA2D(
#         data='striped_0085',
#         clip=True,
#         speed=ctrl | S.To(1, 3),
#         wrapx=True,
#      ) | S.To(0, ctrl | S.To(.3, 1)) | A.HsvMod(0.38)) 
#     #     | A.Overwrite(heart() * S.Const(1.7), 10)
#     )


# @anim
# def happy():
#     # ctrl = N.closest
#     # ctrl = N.v0  # for testing
#     return ((A.NCA2D(
#         data='swirly_0063',
#         clip=True,
#         speed=3.7,
#         wrapx=False,
#     ) | S.To(0, 0.6))
#         | A.Overwrite(heart() * S.Const(1.7), 10)
#     )

# gauzy_0146
@anim
def angry():
    return ((A.NCA2D(
        data='bumpy_0137',
        clip=True,
        speed=3.7,
        wrapx=False,
    ) | A.HsvMod(0.6, 2.0) | S.To(0, N.heart | S.To(.4, 1)))
      | A.Overwrite((heart() * S.Const(1.5)))
    #   | A.Overwrite((heart() * S.Const(N.v1 | S.To(1, 5))) | A.HsvMod(N.v0), 10)
    )
    # ) | A.RGauss(N.heart | S.To(2, 5)
    # ) * (L.Named('std2') | S.Lin(0, 2) | S.Tocos() | A.CompWave(1.8, 2.5)
    # ) * (A.R() | S.Lin( L.Named('v2') | S.To(0, -3) | S.Int(mod=1)) | S.Mod(1)
    # ) | A.SetPixel(1555, C.RGB(0, 1, 0))


@anim
def test():
    return A.FullOn(C.RGB(1, 0, 0))
    # return nca() | A.HsvMod(hue_shift=N.v0, sat_mult=N.v1 | S.To(0, 2))


@anim
def mix():
    return (
        # v0=0
        (S.Const(1) - N.v0) *
        (A.NCA2D('braided_0149', speed=1)
    ) + ((
        # v0=1
        N.v0 *
        A.NCA2D('lacelike_0085', speed=4)
        ) | S.To(0, 0.78))
    )


@anim
def happy():
    ctrl = N.css | S.ElementAt(0) | S.From(0.25, 1) | S.To(0, 1, clip=True)
    return (
        # v0=0
        (A.NCA2D('frilly_0019', speed=4) * (S.Const(1) - ctrl)) | S.To(0, .5) | A.HsvMod(0, 2)
    ) + (
        # v0=1
        (A.NCA2D('stained_0044', speed=4) * ctrl) | A.HsvMod(0, 2)
    )


pixels = (
    (
        # dims dynamically ... needs some tuning
        A.Mixer(animations) | A.Overwrite(heart() * N.anim_heart * S.Const(1.3), 10)

        # dims statically ... loses quite a lot of brightness in head
        # (A.Mixer(animations) | A.Mult(0.5, 'head')) + (heart() * N.anim_heart * S.Const(1.3))
    )
    | A.Mult(N.anim_both)
    | A.Mult(N.anim_head, 'head')
    | A.Mult(N.anim_arms, 'arms')
    | A.HsvMod(hue_shift=N.anim_hue, sat_mult=N.anim_sat)
    | A.Mult(
        L.Named('anim_sig', meta=True) | S.To(.2, 1) | S.Exponential(.1)
    )
    | A.TailSig(ok=C.RGB(0, 1, 0), not_ok=C.RGB(1, 0, 0))
    | S.To(0, N.anim_dark | S.To(1, 0.66))
)
