import functools
import json
import time

import numpy as np  # type: ignore

from smanmi import logic as L, util
from . import mapping, pixel_functions as pf, settings


# mapping
###############################################################################

phi_r_mapping = mapping.generate_arm_configs(settings.arm_configs)
sphere_mapping = phi_r_mapping[: 2 * 8 * 60, :] = (
    mapping.generate_sphere_mapping(settings.sphere_strips, phi0=settings.phi0)
)
kinect_mapping = json.load(open(settings.kinect_mapping_path))
xyz_mapping = mapping.generate_xyz_mapping(
    kinect_mapping, settings.arm_mapping)


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

# Note: This cannot be implemented as a `L.Signal()` because we don't want to
# run the animations that are currently not shown.
class Mixer:
    """Mixes signals by state.state with some interpolation."""

    def __init__(self, animations, default_dt=1, dt_by_state={}):
        self.animations = animations
        self.t0 = 0
        self.default_dt = default_dt
        self.dt_by_state = dt_by_state
        self.current = self.last = 'std'

    def __call__(self, **signals):
        state = signals['state'].state
        t = signals['t']
        if state != self.current:
            self.last = self.current
            self.current = state
            self.t0 = t
        pixels = self.animations[state](**signals)
        dt = self.dt_by_state.get(state, self.default_dt)
        if t - self.t0 < dt:
            v = (t - self.t0) / dt
            last_pixels = self.animations[self.last](**signals)
            pixels = v * pixels + (1 - v) * last_pixels
        return pixels


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


# r-phi
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


class Spiral(L.Signal):
    """Generates a time dependent spiral."""
    
    def init(self, dphi=1, dr=1.5, speed=1):
        pass
    
    def call(self, t):
        return self.speed * t + (
            phi_r_mapping[:, 0] * self.dphi +
            phi_r_mapping[:, 1] * self.dr
        )

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


# debug
###############################################################################
testvar = 0

class PositionIdentify(L.Signal):

    """Color cycle for each of the 8 positions of a given fadecandy."""

    ZEROS = np.zeros((8 * 60, 3), dtype='uint8')
    COLORS = np.concatenate([
        np.zeros((60, 3), dtype='uint8') + col
        for col in (
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 1, 0),
            (1, 0, 1),
            (0, 1, 1),
            (1, 1, 1),
            (0.3, 0.3, 0.3),
        )
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
            col for col in (
                (1, 0, 0),
                (0, 1, 0),
                (0, 0, 1),
                (1, 1, 0),
                (1, 0, 1),
                (0, 1, 1),
                (1, 1, 1),
                (0.3, 0.3, 0.3),
            )
        ]
        self.pixels = np.array([
            colors[int(np.floor((i / 60) % 8))]
            if i % 30 == 0 else [0, 0, 0]
            for i in range(2 * 16 * 60)
        ])

    def call(self):
        """Shows color cycle on NURU."""
        return self.pixels
