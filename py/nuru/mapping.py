"""NURU's NeoPixel mapping.

New improved mapping with both 16x `SphereStripe` (=16x 60 RGB LEDs) and 6x
`ArmConfig` (each 1x or 2x 2x60 RGB LEDs), mapping to a single array of
60x(16+8x2)=1920 pixels.

- the final 1920x3 RGB value pixel is sent to 4x Fadecandy (note each mapping
  480 to 512 pixels by appending 4 ghost pixels after every 60 pixels for a
  single stripe)

- the final 1920x3 RGB value pixel is also set over websocket for display in
  the webapp

- the `(phi, r)`-mapping (1920x2) maps every single pixel to an idealized flat
  space; note that r=1 specifies the rim, but the projection in the sphere and
  on the arms can be variable

- every possible `(x, y, z)` (or `(phi, theta, xi, dist)`) camera position maps
  to a distinct `(x, y)`-mapping (1920x2) for perspective display of a 2D
  surface from a single camera point
"""

from typing import Dict, Mapping, Sequence

import numpy as np  # type: ignore

from . import settings


def generate_sphere_mapping(sphere_strips, r=lambda x: x, phi0=0):
    """Returns a (nx60)x2 mapping from spherical LED index to (phi, r).

    Args:
      sphere_strips: List of SphereStrip.
      r: Function mappig 0..1 to a r.
      phi0: Position of the first LED strip (in degrees).

    Returns:
      Mapping from every LED to (phi[rad], r).
    """
    phi0 *= np.pi / 180
    mapping = np.zeros((60 * len(sphere_strips), 2))
    dphi = 2 * np.pi / len(sphere_strips)
    for led, sphere_strip in enumerate(sphere_strips):
        dr = 1 / (sphere_strip.led0 + sphere_strip.led1)
        phi1 = phi0 + led * dphi
        phi2 = phi1 + dphi / 2
        # going outward
        values = [
            [phi1, r(i * dr)]
            for i in range(sphere_strip.led0,
                           sphere_strip.led0 + sphere_strip.led1)
        ]
        # border
        values += [
            [phi1 + i * dphi / 2 / sphere_strip.border_leds, r(1)]
            for i in range(sphere_strip.border_leds)
        ]
        # going inward
        values += [
            [phi2, r(1 - i * dr)]
            for i in range(
                0, 60 - sphere_strip.led1 - sphere_strip.border_leds)
        ]
        assert len(values) == 60, len(values)
        mapping[led * 60: (led + 1) * 60, :] = np.array(values)
    return mapping


def generate_arm_configs(arm_configs, r=lambda x: 1 + (x - 1) * 2, dphi=3):
    """Returns a (nx60)x2 mapping from arm LED index to (phi, r).

    Args:
      arm_configs: List of ArmConfig.
      r: Function mappig 1..3 to a r.

    Returns:
      Mapping from every LED to (phi[rad], r). The first dimension of the
      returned array will be (1 + max(arm_segment.channel)) * 480.
    """
    n = max([
        arm_segment.channel
        for arm_config in arm_configs
        for arm_segment in arm_config.segments
    ])
    mapping = np.zeros(((n + 1) * 480, 2))
    for arm_config in arm_configs:
        for arm_segment in arm_config.segments:
            for i in range(60):
                pos = i + 60 * (8 * arm_segment.channel + arm_segment.position)
                mapping[pos, 0] = (
                    arm_config.phi + dphi * arm_segment.front) / 180 * np.pi
                mapping[pos, 1] = r(1 + arm_segment.distance + i / 60)
    return mapping


def generate_xyz_mapping(
        kinect_mapping: Sequence[Dict[str, str]],
        arm_mapping: Mapping[str, Sequence[settings.FcPos]],
        sphere_rotate: int = 0):
    """Generates xyz_mapping.

    Args:
      kinect_mapping: Array of dictionaries with:
          - `idx` : '000'..'59' (1m arms) or '000'..'119' (2m arms)
          - `strip_name` (key from `arm_mapping` or 'strip_[0-f]')
          - `co` : list with [x, y, z] coordinates
      arm_mapping: Dictionary mapping arm names to list of `FcPos`. Every 60
          consecutive vertices from `arm_mapping` are mapped to a position on
          a fadecandy.
      strip_rotate: Rotates sphere LEDs by 1/16ths.

    Returns: xyz_mapping[192, 3] of float coordinates.

    Raises:
      AssertionError: If `arm_mapping` covers same pixel mapping space or if
          final mapping has empty spots.
    """

    dmap = {
        strip_name: {
            d['idx']: d['co']
            for d in kinect_mapping
            if d['strip_name'] == strip_name
        }
        for strip_name in set([d['strip_name'] for d in kinect_mapping])
    }

    for i in range(16):
        arm_mapping['strip_{:x}'.format((i + sphere_rotate) % 16)] = [
            settings.FcPos(i // 8, i % 8)
        ]

    xyz_mapping = np.zeros((1920, 3))

    for arm in arm_mapping:
        for fcpos_i, fcpos in enumerate(arm_mapping[arm]):
            xyz = np.array([
                dmap[arm]['{:03}'.format(idx + fcpos_i * 60)]
                for idx in range(60)
            ])
            i0 = fcpos.fadecandy * 8 * 60 + fcpos.pos * 60
            assert (xyz_mapping[i0: i0 + 60] != 0.0).sum() == 0, (arm, fcpos)
            xyz_mapping[i0: i0 + 60] = xyz

    assert (xyz_mapping == 0.0).sum() == 0
    return xyz_mapping


def _generate_sphere_mapping_xy(phi0):
    """Returns a (nx60)x2 mapping from spherical LED index to (x, y).

    Args:
      phi0: Angle (in degrees) of the strip0.

    Returns:
      Mapping from every LED to (x, y) with 0<=x<32 and 0<=6<60.
    """
    mapping = np.zeros((60 * 16, 2), np.int32)
    for idx in range(16):
        x0 = int(idx + phi0 / 360 * 16) * 2
        mapping[idx * 60: idx * 60 + 30] = [
            [x0 % 32, y] for y in range(30)
        ]
        mapping[idx * 60 + 30: idx * 60 + 60] = [
            [(x0 + 1) % 32, y] for y in range(30 - 1, 0 - 1, -1)
        ]
    return mapping


def _generate_arms_mapping_xy(arm_configs):
    """Returns a (nx60)x2 mapping from arm LED index to (phi, r).

    Args:
      arm_configs: List of ArmConfig.
      r: Function mappig 1..3 to a r.

    Returns:
      Mapping from every LED to (x, y) with 0<=x<32 and 60<=6<180.
    """
    n = max([
        arm_segment.channel
        for arm_config in arm_configs
        for arm_segment in arm_config.segments
    ])
    mapping = np.zeros(((n + 1) * 480, 2), np.int32)
    for arm_config in arm_configs:
        for arm_segment in arm_config.segments:
            x0 = int(16 * arm_config.phi / 360)
            for i in range(60):
                pos = i + 60 * (8 * arm_segment.channel + arm_segment.position)
                mapping[pos, 0] = (x0 + int(arm_segment.front)) % 32
                mapping[pos, 1] = 30 + 60 * arm_segment.distance + i
    return mapping


def generate_xy_mapping(phi0: float,
        arm_mapping: Mapping[str, Sequence[settings.FcPos]]) -> np.ndarray:
    xy_mapping = _generate_arms_mapping_xy(settings.arm_configs)
    xy_mapping[: 2 * 8 * 60, :] = _generate_sphere_mapping_xy(settings.phi0)
    return xy_mapping


is_head = np.array([i < 2 * 8 * 60 for i in range(1920)])