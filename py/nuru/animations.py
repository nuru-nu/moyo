import collections, functools, json, time

import numpy as np

from smanmi import logic as L, util
from . import mapping, pixel_functions as pf, settings


# mapping
###############################################################################


phi_r_mapping = mapping.generate_arm_configs(settings.arm_configs)
phi_r_mapping[:2*8*60, :] = mapping.generate_sphere_mapping(
    settings.sphere_strips, phi0=settings.phi0)


# utils
###############################################################################


def full_on(color, nr_pixels):
    return np.tile(color, nr_pixels).reshape(nr_pixels, -1)


def linear(x):
    return x


def r_piecewise(r, inner_mult=np.pi/2, outer_mult=0.5):
    """Multiplies r with different factors for inner/outer area."""
    return np.piecewise(
        r,
        [r < 1, r >= 1],
        [lambda r: r * inner_mult, lambda r: (r - 1) * outer_mult + inner_mult]
    )


def phi_r_transform(r_phi_mapping, inner_mult=np.pi/2, outer_mult=0.5):
    """Transforms both r & phi."""
    return np.hstack([
        r_phi_mapping[:, 0:1],
        r_piecewise(r_phi_mapping[:, 1:2], inner_mult=inner_mult, outer_mult=outer_mult),
    ])


# state related
###############################################################################


# TODO subclass L.Signal
class Mixer:
    """Mixes signals by state.state with some interpolation."""

    def __init__(self, d, default_dt=1, dt_by_state={}):
        self.d = d
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
        pixels = self.d[state](**signals)['value']
        dt = self.dt_by_state.get(state, self.default_dt)
        if t - self.t0 < dt:
            v = (t - self.t0) / dt
            last_pixels = self.d[self.last](**signals)['value']
            pixels = v * pixels + (1 - v) * last_pixels
        return dict(value=pixels)


# animation combiners
###############################################################################


# TODO subclass L.Signal
class Add:

    def __init__(self, *anims):
        self.anims = anims

    def __call__(self, **signals):
        pixels = self.anims[0](**signals)['value']
        for anim in self.anims[1:]:
            pixels += anim(**signals)['value']
        return dict(value=pixels)


# simple animations
###############################################################################


class FullOn(L.Signal):
    def init(self, color):
        pass

    def call(self):
        return np.repeat([self.color], phi_r_mapping.shape[0], axis=0)


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

    def init(self, sigma, color, phi, r, inner_mult=np.pi/2):
        self.spherical_mask = phi_r_mapping[:, 1:2] < 1

    def call(self):
        return pf.spherical_gaussian_droplet(
            phi_r_mapping, [self.phi, self.r], self.sigma, self.color
        ) * (phi_r_mapping[:, 1:2] < np.pi)
        # FIXME
        # return pf.spherical_gaussian_droplet(
        #     phi_r_mapping, [self.phi, self.r], self.sigma, self.color
        # ) * self.spherical_mask + pf.r_phi_gaussian_1d(
        #     phi_r_mapping, [self.phi, self.r], self.sigma, self.color
        # ) * (~self.spherical_mask)


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


# debug
###############################################################################


class PositionIdentify(L.Signal):

    """Color cycle for each of the 8 positions of a given fadecandy."""

    ZEROS = np.zeros((8*60, 3), dtype='uint8')
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

    def call(self, fc=None):
        """Shows color cycle on fadecandy specified by `fc`."""
        return np.concatenate([
            self.COLORS if i==fc else self.ZEROS
            for i in range(settings.fadecandies)
        ])
