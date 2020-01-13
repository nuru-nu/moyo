import numpy as np

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


def generate_arm_configs(arm_configs, r=lambda x: 1 + (x-1)*2, dphi=3):
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
                pos = i + 60 * (8*arm_segment.channel + arm_segment.position)
                mapping[pos, 0] = (arm_config.phi + dphi*arm_segment.front) / 180 * np.pi
                mapping[pos, 1] = r(1 + arm_segment.distance + i / 60)
    return mapping

