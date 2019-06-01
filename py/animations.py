
import time

import colorsys
import numpy as np

import logic as L, pixel_functions as pf, settings, util


mapping = settings.load_mapping()


# utils
###############################################################################


def full_on(color, nr_pixels):
    return np.tile(color, nr_pixels).reshape(nr_pixels, -1)


class Noop(L.Signal):
    def init(self, dt=0):
        self.logger = util.PrintEvery(dt)

    def call(self, value):
        self.logger('Noop: value={}'.format(value))
        return value

# state related
###############################################################################


# TODO subclass L.Signal
class Mixer:
    """Mixes signals by state.state with some interpolation."""

    def __init__(self, d):
        self.d = d
        self.t0 = 0
        self.dt = 1
        self.current = self.last = 'std'

    def __call__(self, **signals):
        state = signals['state'].state
        t = signals['t']
        if state != self.current:
            self.last = self.current
            self.current = state
            self.t0 = t
        pixels = self.d[state](**signals)['value']
        if t - self.t0 < self.dt:
            v = (t - self.t0) / self.dt
            last_pixels = self.d[self.last](**signals)['value']
            pixels = v * pixels + (1 - v) * last_pixels
        return dict(value=pixels)

# color
###############################################################################


class RGB(L.Signal):
    def init(self, r, g, b):
        pass

    def call(self):
        return [self.r, self.g, self.b]


class HSV(L.Signal):
    def init(self, hue=1, saturation=1, value=1):
        pass

    def call(self):
        return colorsys.hsv_to_rgb(
            self.hue,
            self.saturation,
            self.value)

# simple animations
###############################################################################


class FullOn(L.Signal):
    def init(self, color):
        pass

    def call(self):
        return full_on(self.color, settings.sphere_pixels)

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


class ThetaRing(L.Signal):
    def init(self, phi, width, color):
        pass

    def call(self):
        return pf.theta_ring(
            mapping,
            phi=self.phi,
            width=self.width,
            color=self.color,
        )


class PhiRing(L.Signal):
    def init(self, theta, width, color):
        pass

    def call(self):
        return pf.phi_ring(
            mapping,
            theta=self.theta,
            width=self.width,
            color=self.color,
        )

# gaussians
###############################################################################


class GaussianDroplet(L.Signal):

    def init(self, sigma, color, phi, theta):
        pass

    def call(self):
        return pf.gaussian_droplet(
            mapping, [self.phi, self.theta], self.sigma, self.color)


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
        pixels = np.zeros((len(mapping), 3))
        for drop_nr in range(self.nr_droplets):
            if (time.time() - self.t_0s[drop_nr]) / self.drop_duration > 1:
                self.t_0s[drop_nr] = time.time()
                phi, theta = util.phi_theta_samples(1)
                self.positions[drop_nr] = [phi[0] - np.pi, 2 * theta[0]]
                # self.positions[drop_nr] = [pf.rand_range((-np.pi, np.pi)), pf.rand_range((0, np.pi))]  # noqa
                self.colors[drop_nr] = self.color

            dt = time.time() - self.t_0s[drop_nr]
            sigma = self.radius * dt / self.drop_duration

            pixels += pf.gaussian_droplet(
                mapping, self.positions[drop_nr], sigma, self.colors[drop_nr])

        return pixels

# arms
###############################################################################


class ArmFullOn(L.Signal):
    def init(self, arm_config, color, mult=1):
        pass

    def call(self):
        return np.concatenate([
            full_on(self.color, 64)
            for offsets in self.arm_config.offsets
            for offset in offsets
        ]) * self.mult


class ArmGradient(L.Signal):

    def init(self, arm_config, color, func=lambda x: x, mult=1):
        """Func is a scalar function mapping 0..1 to a value."""

    def call(self):
        pixels = np.concatenate([
            full_on(self.color, 64)
            for offsets in self.arm_config.offsets
            for offset in offsets
        ]) * self.mult

        length = len(self.arm_config.offsets)
        dist = np.concatenate([
            np.tile(np.concatenate([
                np.linspace(meter, meter + 1, 60) / length,
                [0.0] * 4,
            ]), len(offsets))
            for meter, offsets in enumerate(
                self.arm_config.offsets)
        ])
        return np.array([
            pixel * self.func(d)
            for d, pixel in zip(dist, pixels)
        ])


class ArmRing(L.Signal):

    def init(self, arm_config, value, color, width):
        """value : where the ring is (0..1)"""

    def call(self):
        pixels = np.concatenate([
            full_on(self.color, 64)
            for offsets in self.arm_config.offsets
            for offset in offsets
        ])
        length = len(self.arm_config.offsets)
        dist = np.concatenate([
            np.tile(np.concatenate([
                np.linspace(meter, meter + 1, 60) / length,
                [0.0] * 4,
            ]), len(offsets))
            for meter, offsets in enumerate(
                self.arm_config.offsets)
        ])
        return np.array([
            pixel * (np.abs(self.value - d) < self.width / 2)
            for d, pixel in zip(dist, pixels)
        ])
