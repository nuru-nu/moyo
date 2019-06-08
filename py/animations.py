import collections, json, time

import colorsys
import numpy as np

import logic as L, pixel_functions as pf, settings, util

# mapping
###############################################################################


# LEGACY
def load_mapping():
    mapping = np.zeros((settings.sphere_pixels, 2))
    with open(settings.get_mapping_path()) as json_file:
        data = json.load(json_file)
        for coord_data in data:
            idx = int(coord_data['idx'])
            phi = float(coord_data['phi'])
            theta = float(coord_data['theta'])
            # phi: -pi - pi, theta 0 - pi
            mapping[idx - 1] = np.array([phi, theta])
    return mapping


def generate_sphere_mapping(phi0):
    mapping = np.zeros((64 * len(settings.sphere_strips), 2))
    dphi = 2 * np.pi / len(settings.sphere_strips)
    for led, sphere_strip in enumerate(settings.sphere_strips):
        dtheta = np.pi / 2 / (sphere_strip.led0 + sphere_strip.led1)
        phi1 = phi0 + led * dphi
        phi2 = phi1 + dphi / 2
        # going outward
        values = [
            [phi1, i * dtheta]
            for i in range(sphere_strip.led0,
                           sphere_strip.led0 + sphere_strip.led1)
        ]
        # border
        values += [
            [phi1 + i * dphi / 2 / sphere_strip.border_leds, np.pi / 2]
            for i in range(sphere_strip.border_leds)
        ]
        # going inward
        values += [
            [phi2, np.pi / 2 - i * dtheta]
            for i in range(
                0, 60 - sphere_strip.led1 - sphere_strip.border_leds)
        ]
        assert len(values) == 60, len(values)
        mapping[led * 64: led * 64 + 60, :] = np.array(values)
    return mapping


def arm_dists(arm_config):
    length = len(arm_config.offsets)
    return np.concatenate([
        np.tile(np.concatenate([
            np.linspace(meter, meter + 1, 60) / length,
            [0.0] * 4,
        ]), len(offsets))
        for meter, offsets in enumerate(arm_config.offsets)
    ])


def generate_arm_mapping():
    mapping_by_channel = {}
    for arm_segment in settings.arm_segments:
        if arm_segment.channel not in mapping_by_channel:
            mapping_by_channel[arm_segment.channel] = np.zeros((512, 2))
        pixels = mapping_by_channel[arm_segment.channel]
        i0 = 64 * arm_segment.output
        pixels[i0: i0 + 60, 0] = arm_segment.phi
        pixels[i0: i0 + 60, 1] = np.linspace(
            arm_segment.start, arm_segment.stop, 60)
    return mapping_by_channel


def generate_total_mapping(phi0):
    """Returns is_sphere, mapping [(phi, theta), ...] for sphere & all arms.

    The pixels in the sphere have phi 0..2pi and theta 0..pi/2, while the
    pixels of the arms have phi 0..2pi and "theta" 0..1 (for short arms) or
    0..2 (for long arms).
    """
    sc1 = settings.sphere_channel1
    sc2 = settings.sphere_channel2
    channel_max = max(
        sc1, sc2,
        *[segment.channel for segment in settings.arm_segments])
    total_mapping = np.zeros((512 * channel_max, 2))
    is_sphere = np.zeros(total_mapping.shape[0])
    sphere_mapping = generate_sphere_mapping(phi0)
    total_mapping[(sc1 - 1) * 512: sc1 * 512] = sphere_mapping[:512]
    total_mapping[(sc2 - 1) * 512: sc2 * 512] = sphere_mapping[512:]
    is_sphere[(sc1 - 1) * 512: sc1 * 512] = 1.0
    is_sphere[(sc2 - 1) * 512: sc2 * 512] = 1.0
    for channel, segment_mapping in generate_arm_mapping().items():
        total_mapping[(channel - 1) * 512: channel * 512] = segment_mapping
    return is_sphere, total_mapping


if settings.is_blender:
    sphere_mapping = load_mapping()
else:
    sphere_mapping = generate_sphere_mapping(phi0=122 * settings.dg)
    is_sphere, total_mapping = generate_total_mapping(phi0=122 * settings.dg)

# utils
###############################################################################


def full_on(color, nr_pixels):
    return np.tile(color, nr_pixels).reshape(nr_pixels, -1)


def linear(x):
    return x


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


ColorPoint = collections.namedtuple('ColorPoint', ['index', 'color'])


def parse_colors_co_scss(scss):
    rgbs = [
        [float(v) / 256
         for v in line[line.index('(') + 1:line.index(')')].split(', ')[:3]]
        for line in scss.split('\n')
        if line
    ]
    return [
        ColorPoint(i / len(rgbs), rgb)
        for i, rgb in enumerate(rgbs)
    ]


def hex_to_tuple(s):
    if s[0] == '#':
        s = s[1:]
    if len(s) == 3:
        return tuple((
            0x10 * int(c, 0x10) / 256
            for c in s
        ))
    elif len(s) == 6:
        return tuple((
            int(s[i * 2: (i + 1) * 2], 0x10) / 256
            for i in range(len(s) // 2)
        ))
    else:
        raise ValueError('invalid hex: {}'.format(s))


def parse_colors_hex(indexes_and_hexes):
    return [
        ColorPoint(index, hex_to_tuple(hex_s))
        for index, hex_s in indexes_and_hexes
    ]


class HSV(L.Signal):
    def init(self, hue=1, saturation=1, value=1):
        pass

    def call(self):
        return colorsys.hsv_to_rgb(
            self.hue,
            self.saturation,
            self.value)


class Palette:
    """Generates array of colors with precomputed interpolated palette."""

    def __init__(self, colors, n=256):
        self.n = n
        xs = np.linspace(0, 1, n)
        self.lookup = np.array([
            np.interp(
                xs, [c.index for c in colors], [c.color[i] for c in colors])
            for i in range(3)
        ]).T

    def __call__(self, values):
        return self.lookup[(np.clip(values, 0, 1) * (self.n - 1)).astype(int)]



class StatePalette(L.Signal):
    def init(self, default_palette, palettes_dict):
        pass

    def call(self, state):
        return self.palettes_dict.get(
            state.color,
            self.default_palette
        )


class ColorPalette(L.Signal):
    def init(self, colors, n=256):
        xs = np.linspace(0, 1, n)
        self.lookup = np.array([
            np.interp(
                xs, [c.index for c in colors], [c.color[i] for c in colors])
            for i in range(3)
        ]).T

    def call(self, value):
        return self.lookup[
            (np.clip(value, 0, 1) * (self.n - 1)).astype(int), :]

# TODO make this work with SimpleSignal
class RedToPalette(L.Signal):
    """Converts the red channel of a (legacy) animation to a color palette."""

    # (just subclassing for the __or__ operator)

    def __init__(self, colors):
        if not hasattr(colors, '__call__'):
            colors = ColorPalette(colors)
        self.color_palette = colors

    def __call__(self, value, **kw):
        red_values = value[:, 0]
        colors = self.color_palette(value=red_values)['value']
        return dict(value=colors)


# simple animations
###############################################################################


class FullOn(L.Signal):
    def init(self, color):
        pass

    def call(self):
        return full_on(self.color, len(sphere_mapping))

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
            sphere_mapping,
            phi=self.phi,
            width=self.width,
            color=self.color,
        )


class PhiRing(L.Signal):
    def init(self, theta, width, color):
        pass

    def call(self):
        return pf.phi_ring(
            sphere_mapping,
            theta=self.theta,
            width=self.width,
            color=self.color,
        )


class ThetaPalette(L.Signal):
    """Computes palette along theta."""

    def init(self, palette, shift=0, mult=1, func=linear):
        """Computes palette[func(shift + theta/(pi/2) * mult)]."""
        global sphere_mapping
        self.dists = sphere_mapping[:, 1] / (np.pi / 2)

    def call(self):
        return self.palette(
            self.func((self.shift + self.dists * self.mult) % 1))


class ThetaPaletteWindow(L.Signal):
    """Computes palette along theta, windowed on range from a value."""

    def init(self, palette, start, end):
        global sphere_mapping
        self.dists = sphere_mapping[:, 1] / (np.pi / 2)

    def call(self, value):
        return self.palette(self.dists)


class PhiPalette(L.Signal):
    """Computes palette along phi."""

    def init(self, palette, shift=0, mult=1, func=linear):
        """Computes palette[func(shift + theta/(pi/2) * mult)]."""
        global sphere_mapping
        self.dists = sphere_mapping[:, 0] / (np.pi * 2)

    def call(self):
        return self.palette(
            self.func((self.shift + self.dists * self.mult) % 1))

# gaussians
###############################################################################


class GaussianDroplet(L.Signal):

    def init(self, sigma, color, phi, theta):
        pass

    def call(self):
        return pf.gaussian_droplet(
            sphere_mapping, [self.phi, self.theta], self.sigma, self.color)


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
        pixels = np.zeros((len(sphere_mapping), 3))
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
                sphere_mapping,
                self.positions[drop_nr], sigma, self.colors[drop_nr])

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

    def init(self, arm_config, color, func=lambda x: 1 - x, mult=1):
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


class ArmPalette(L.Signal):
    """Computes palette along arm."""

    def init(self, arm_config, palette, shift=0, mult=1, func=linear):
        self.dists = arm_dists(arm_config)

    def call(self):
        return self.palette(
            self.func((self.shift + self.dists * self.mult) % 1))


class ArmPaletteWindow(L.Signal):
    """Computes palette along arm, windowed on range of a value."""

    def init(self, arm_config, palette, start, end):
        self.dists = arm_dists(arm_config)

    def call(self, value):
        return self.palette(
            self.dists * (value - self.start) * (self.end - self.start))


class ArmByDist(L.Signal):

    def init(self, arm_config, func):
        dists = arm_dists(arm_config)
        self.M = np.tile(func(dists), 3).reshape(3, -1).T

    def call(self, value):
        return value * self.M


class ArmIdentify(L.Signal):
    """Helper to solve mapping problems."""

    _COLOR_CYCLE = [
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 0, 1),
    ]

    def init(self, arm_config):
        values = []
        i = 0
        n = len(self._COLOR_CYCLE)
        for offsets in arm_config.offsets:
            for offset in offsets:
                values += [self._COLOR_CYCLE[i % n]] * 64
                i += 1
        self.values = np.array(values)

    def call(self):
        return self.values
