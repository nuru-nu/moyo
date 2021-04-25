import functools
import json
import time

import numpy as np  # type: ignore
from scipy import stats

# TODO import async
from self_organising_systems.texture_ca import ca
import tensorflow as tf

from smanmi import logic as L, util
from smanmi.midi import Command
from . import mapping, pixel_functions as pf, settings


# Members are set inside L.Signal.__init__() ...
# pylint: disable=no-member


# mapping
###############################################################################

phi_r_mapping = mapping.generate_arm_configs(settings.arm_configs)
sphere_mapping = phi_r_mapping[: 2 * 8 * 60, :] = (
    mapping.generate_sphere_mapping(settings.sphere_strips, phi0=settings.phi0)
)
kinect_mapping = json.load(open(settings.kinect_mapping_path))
xyz_mapping = mapping.generate_xyz_mapping(
    kinect_mapping, settings.arm_mapping)
xy_mapping = mapping.generate_xy_mapping(settings.phi0, settings.arm_mapping)


# utils
###############################################################################

def r_piecewise(r, inner_mult=np.pi / 2, outer_mult=0.5):
    """Multiplies r with different factors for inner/outer area."""
    return np.piecewise(
        r,
        [r < 1, r >= 1],
        [lambda r: r * inner_mult, lambda r: (r - 1) * outer_mult + inner_mult]
    )


# state related
###############################################################################

class Mixer(L.Signal):
    """Mixes signals by state.state with some interpolation."""

    def init(self, animations, default_dt=1, dt_by_state={}):
        self.t0 = 0
        self.current = self.last = 'off'

    def call(self, animation, t, **signals):
        if animation != self.current:
            self.last = self.current
            self.current = animation
            self.t0 = t
        pixels = self.animations[animation](t=t, **signals)
        dt = self.dt_by_state.get(animation, self.default_dt)
        if t - self.t0 < dt:
            v = (t - self.t0) / dt
            last_pixels = self.animations[self.last](t=t, **signals)
            pixels = v * pixels + (1 - v) * last_pixels
        return pixels


class MidiMixer(L.Signal):
    """Mixes signals by MIDI activation with some interpolation."""

    def init(self, notes_to_animations, dt=1.0):
        self.anim = self.lanim = list(notes_to_animations.values())[0]
        self.lt = 0

    def update(self, t, midi):
        command = Command.parse(midi)
        if command.command != 'on':
            return
        anim = self.notes_to_animations.get(command.note)
        if not anim or anim == self.anim:
            return
        self.lt = t
        self.lanim, self.anim = self.anim, anim

    def call(self, t, midi, **signals):
        if midi:
            self.update(t, midi)
        v = (t - self.lt) / self.dt
        signals = dict(t=t, midi=midi, **signals)
        if v > 1:
            return self.anim(**signals)
        return self.lanim(**signals) * (1 - v) + v * self.anim(**signals)


# mixing
###############################################################################

class Max(L.Signal):
    """Keeps maximum of RGB values from provided animations."""

    def init(self, anim1, anim2):
        pass

    def call(self):
        return np.transpose([self.anim1, self.anim2], [1, 2, 0]).max(axis=-1)


class Sum(L.Signal):
    """Sums RGB values from provided animations."""

    def init(self, anim1, anim2):
        pass

    def call(self):
        x = np.transpose([self.anim1, self.anim2], [1, 2, 0]).sum(axis=-1)
        return np.clip(x, 0, 1)

# animation combiners
###############################################################################

def add(anims):
    """Reduces an iterable of animations by addition."""
    return functools.reduce(lambda acc, a: acc + a, anims[1:], anims[0])


# simple animations
###############################################################################

class Ones(L.Signal):
    """All pixels same value."""

    def init(self):
        self.value = np.ones([len(phi_r_mapping)], float)

    def call(self):
        return self.value


class FullOn(L.Signal):
    """Single color for all pixels."""

    def init(self, color):
        self.ones = np.ones([len(phi_r_mapping)], float)[:, None]

    def call(self):
        return self.color[None] * self.ones


class RPalette(L.Signal):
    """Computes palette along r."""

    def init(self, palette, shift=0, mult=1, func=r_piecewise):
        """Computes palette[(shift + func(r)*mult) % 1]."""

    def call(self):
        return self.palette(
            ((self.shift + self.func(phi_r_mapping[:, 1]) * self.mult) % 1))


class PhiPalette(L.Signal):
    """Computes palette along phi."""

    def init(self, palette, shift=0, mult=1, func=lambda phi: phi / 2 / np.pi):
        """Computes palette[(shift + func(phi)*mult) % 1]."""

    def call(self):
        return self.palette(
            ((self.shift + self.func(phi_r_mapping[:, 0]) * self.mult) % 1))


# gaussians
###############################################################################

class GaussianActivation(L.Signal):
    """Bright gaussians at people's xy-center of mass."""

    def init(self, min=0.3, std=1):
        pass

    def call(self, value, people):
        tot = np.ones(len(xyz_mapping)) * self.min
        g = stats.norm(0, self.std)
        for p in people:
            if 'cm' not in p: continue
            xyz = np.array(p['cm'])
            # xyz[0] *= -1
            dist = ((xyz_mapping - xyz)**2).sum(axis=1)**.5
            act = g.pdf(dist) / g.pdf(0)
            tot += act
            # if not hasattr(self, '_debug'):
            #     print(p, dist)
            #     print(p, act)
            #     setattr(self, '_debug', True)
        return value * tot[:, None]

class RGauss(L.Signal):
    """Applies radial denormalized normal-shaped activation to value."""

    def init(self, sigma):
        pass

    def call(self, value):
        g = stats.norm(0, self.sigma).pdf
        return value * g(phi_r_mapping[:, 1])[:, None] / g(0)

class GaussianDroplet(L.Signal):

    def init(self, sigma, phi, r, inner_mult=np.pi / 2):
        self.spherical_mask = phi_r_mapping[:, 1] < 1

    def call(self):
        # return pf.spherical_gaussian_droplet(
        #     phi_r_mapping, [self.phi, self.r], self.sigma
        # ) * self.spherical_mask
        return pf.r_phi_gaussian_2d(
            phi_r_mapping, [self.phi, self.r], self.sigma
        )  # * (~self.spherical_mask)


class GaussianRain(L.Signal):

    def init(self, nr_droplets, radius, drop_duration, color):
        self.t_0s = [time.time() + 5 * np.random.rand(1)[0]
                     for _ in range(int(self.nr_droplets))]
        self.positions = [
            [pf.rand_range((-np.pi, np.pi)), pf.rand_range((0, np.pi))]
            for _ in range(int(self.nr_droplets))
        ]
        self.colors = [[0, 0, 0] for _ in range(int(self.nr_droplets))]

    def call(self):
        def rand_range(lims):
            return lims[0] + (lims[1] - lims[0]) * np.random.rand(1)[0]
        pixels = np.zeros((len(sphere_mapping), 3))
        for drop_nr in range(self.nr_droplets):
            if (time.time() - self.t_0s[drop_nr]) / self.drop_duration > 1:
                self.t_0s[drop_nr] = time.time()
                phi, theta = util.phi_theta_samples(1)
                self.positions[drop_nr] = [phi[0] - np.pi, 2 * theta[0]]
                # self.positions[drop_nr] = [rand_range((-np.pi, np.pi)), rand_range((0, np.pi))]  # noqa
                self.colors[drop_nr] = self.color

            dt = time.time() - self.t_0s[drop_nr]
            sigma = self.radius * dt / self.drop_duration

            pixels += pf.gaussian_droplet(
                sphere_mapping,
                self.positions[drop_nr], sigma, self.colors[drop_nr])

        return pixels


# phi-r
###############################################################################

class R(L.Signal):
    """Returns radius."""

    def call(self):
        return phi_r_mapping[:, 1]


class Phi(L.Signal):
    """Returns phi."""

    def call(self):
        return phi_r_mapping[:, 0]


class Dist2D(L.Signal):
    """Distance from point in euclidian phi/r plane."""

    def init(self, phi, r):
        self.lphi = self.lr = None
        self.ldist = None

    def call(self):
        if self.phi != self.lphi or self.r != self.lr:
            phi, r = phi_r_mapping.T
            self.ldist = (
                (r * np.cos(phi) - self.r * np.cos(self.phi)) ** 2 +
                (r * np.sin(phi) - self.r * np.sin(self.phi)) ** 2
            ) ** .5
            self.lphi = self.phi
            self.lr = self.r
        return self.ldist


class PhiRXY(L.Signal):
    """X, Y cooordinates derived from phi_r_mapping.

    Use in combination like `A.PhiRXY() | S.T() | S.ElementAt(0)`.
    """

    def init(self, dg):
        pass

    def call(self):
        phi, r = phi_r_mapping.T
        dphi = np.pi / 180 * self.dg
        return np.vstack([
            r * np.sin(phi + dphi),
            r * np.cos(phi + dphi),
        ]).T


class Spiral(L.Signal):
    """Static spiral."""

    def init(self, dr=1, n=1):
        pass

    def call(self, t):
        phi, r = phi_r_mapping.T
        return r * self.dr + phi / 2 / np.pi * self.n


class Aliasing(L.Signal):
    """Buggy spiral generating fancy aliasing patterns."""

    def init(self, speed=1, aspect=0):
        self.lt = None
        self.value = np.zeros(len(phi_r_mapping))

    def call(self, t):
        if self.lt is None:
            self.lt = t
        dt = t - self.lt
        self.lt = t
        phi, r = phi_r_mapping.T
        self.value += self.speed * dt * (
            r + phi / 2 / np.pi * self.aspect
        )
        return self.value


# 3D
###############################################################################

class Dist3D(L.Signal):
    """Calculates distance in 3D."""

    def init(self, x=0, y=0, z=0):
        self.lxyz = xyz = (x, y, z)
        self.dist = self._dist(*xyz)

    def dump(self):
        print(self.dist)

    def _dist(self, x, y, z):
        return np.linalg.norm(xyz_mapping - [[x, y, z]], axis=1)

    def call(self):
        xyz = (self.x, self.y, self.z)
        if self.lxyz != xyz:
            self.dist = self._dist(*xyz)
            self.lxyz = xyz
        return self.dist


class CompWave(L.Signal):
    """Use: sig | CompWave() | Gradient."""

    def init(self, start=1.5, stop=1.8):
        r = phi_r_mapping[:, 1]
        self.x = r / r.max()

    def call(self, value):
        exp = self.start + value * (self.stop - self.start)
        u = np.exp((1.5 - self.x) * exp)
        return 0.5 + 0.5 * np.sin(u)



# noise
###############################################################################

class NoiseCycle(L.Signal):
    """Cycles through noise patterns."""

    def init(self, hz):
        self.dt = 0
        self.t0 = None
        self.pattern1 = self._create_noise()
        self.pattern2 = self._create_noise()

    def _create_noise(self):
        return np.random.uniform(size=len(phi_r_mapping))

    def call(self, t):
        if self.t0 is not None:
            self.dt += (t - self.t0) * self.hz
        self.t0 = t
        if self.dt > 1:
            self.pattern1 = self.pattern2
            self.pattern2 = self._create_noise()
            self.dt -= int(self.dt)
        return self.pattern1 * (1 - self.dt) + self.pattern2 * self.dt


# image
###############################################################################

class Proj(L.Signal):
    """Projects xyz onto 2D image, then applies linear transforms."""
    
    def init(self, image, scale=1, rotate=0, dx=0, dy=0):
        """Applies in order : scale -> rotate (deg) -> translate."""
        self.current = None

    def _init(self):
        if self.image is self.current:
            return
        h, w, _ = self.h, self.w, _ = self.image.shape
        xmin, _, zmin = xyz_mapping.min(axis=0)
        xmax, _, zmax = xyz_mapping.max(axis=0)

        # Center to center, scale to fit.
        fx =  (w/2 -1) / max(abs(xmin), abs(xmax))
        fy = -(h/2 -1) / max(abs(zmin), abs(zmax))
        proj = np.array([
            [fx, 0, 0, w/2],
            [0, 0, fy, h/2],
            [0, 0, 0, 1],
        ])
        xyz1 = np.hstack([xyz_mapping, np.ones((len(xyz_mapping), 1))])
        self.xy1 = xyz1 @ proj.T
        self.current = self.image

    def scaleT(self):
        return np.array([
            [self.scale, 0, (self.w - self.w*self.scale)/2],
            [0, self.scale, (self.h - self.h*self.scale)/2],
            [0, 0, 1],
        ]).T

    def translateT(self, dx=None, dy=None):
        """Note : dx points rightwards, dy upwards (mathematical convention)."""
        if dx is None: dx = self.dx
        if dy is None: dy = self.dy
        return np.array([
            [1, 0,  dx * self.w],
            [0, 1, -dy * self.h],
            [0, 0, 1],
        ]).T

    def rotateT(self):
        # Remember : translateT(-.5, .5) moves center to origin (y "inverted").
        phi = self.rotate / 180 * np.pi
        return self.translateT(-.5, .5) @ np.array([
            [np.cos(phi), -np.sin(phi), 0],
            [np.sin(phi),  np.cos(phi), 0],
            [0, 0, 1],
        ]).T @ self.translateT(.5, -.5)

    def xy(self):
        xy1 = self.xy1 @ self.scaleT() @ self.rotateT() @ self.translateT()
        return xy1[:, :2]

    def debug(self, k=10):
        # Inpaint it black.
        image = np.array(self.image)
        for x, y in self.xy():
            x, y = int(x), int(y)
            if 0 <= x <= self.w - 1 and 0 <= y <= self.h - 1:
                image[y:y+k, x:x+k, :] = 0
        return image

    def call(self):
        self._init()
        xy = self.xy()
        x = np.clip(xy[:, 0], 0, self.w - 1)
        y = np.clip(xy[:, 1], 0, self.h - 1)
        pixels = self.image[y.astype(int), x.astype(int)]
        if pixels.max() > 1:
            raise AssertionError('Make sure `image` has normalized RGB!')
        return pixels


# machine learnt
###############################################################################

class NCA2D(L.Signal):
    """Runs a neural cellular automaton in 2D & retrieves mapped pixels."""

    def init(self, data, mapping, speed=1, height=150, width=32, channel_n=12,
             wrapx=True, base='nca'):
        self.last_data = None
        if wrapx:
            width += 2
        self.x = tf.zeros([1, height, width, channel_n])
        self.counter = 0
        self.m = tf.constant(mapping)

    def call(self):
        if self.last_data != self.data:
            data = self.data
            if isinstance(data, str):
                print('LOADING', data)
                data = np.load(f'{self.base}/{data}.npy', allow_pickle=True)
            self.f = ca.CAModel(data).embody()
            self.x = tf.zeros_like(self.x)
            self.last_data = self.data
        self.counter += 1
        while self.counter >= 1/self.speed:
            if self.wrapx:
                w = self.x.shape[2]
                self.x = tf.concat([
                    self.x[:, :, 0: 1, :],
                    self.x[:, :, 1: w-1, :],
                    self.x[:, :, w-1:w, :],
                ], axis=2)
            self.x = self.f(self.x)
            self.counter -= 1/self.speed
        self.img = ca.to_rgb(self.x)[0].numpy()
        return self.img[self.m[:, 1], self.m[:, 0], :]


# debug
###############################################################################

IDENT_COLORS = (
        (1, 0, 0), # 0 red
        (0, 1, 0), # 1 green
        (0, 0, 1), # 2 blue
        (1, 1, 0), # 3 yellow
        (1, 0, 1), # 4 magenta
        (0, 1, 1), # 5 turquise
        (1, 1, 1), # 6 white
        (0.3, 0.3, 0.3), # 7 gray
)

class PositionIdentify(L.Signal):
    """Color cycle for each of the 8 positions of a given fadecandy."""

    ZEROS = np.zeros((8 * 60, 3))
    COLORS = np.concatenate([
        np.zeros((60, 3)) + col
        for col in IDENT_COLORS
    ])

    def call(self, fc):
        """Shows color cycle on fadecandy specified by `fc`."""
        return np.concatenate([
            self.COLORS if i == fc else self.ZEROS
            for i in range(settings.fadecandies)
        ])


class CalibrationPattern(L.Signal):
    """Color cycle for reference points to identify NURU layout."""

    def init(self):
        colors = [
            col for col in IDENT_COLORS
        ]
        self.pixels = np.array([
            colors[int(np.floor((i / 60) % 8))]
            if i % 30 == 0 else [0, 0, 0]
            for i in range(2 * 16 * 60)
        ])

    def call(self):
        """Shows color cycle on NURU."""
        return self.pixels