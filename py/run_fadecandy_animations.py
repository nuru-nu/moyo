import json, socket

import numpy as np
import opc  # NOQA

import hotplug, settings, state, util


logger = util.createLogger('fadecandy')
hp = hotplug.HotPlug(logger, modules=('animations',))

# client = opc.Client('localhost:7890')
# client.set_interpolation(False)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

sock.settimeout(None)
sock.bind((settings.address, settings.fadecandy_port))

signals = {}

arm_channels = set(arm_config.channel for arm_config in settings.arm_configs)
all_arm_pixels = {
    channel: (
        # TODO dirty hack !
        np.zeros([10 * 64, 3]) if channel == 3
        else np.zeros([8 * 64, 3])
    )
    for channel in arm_channels
}

last_t = 0
while True:
    try:
        data, address = sock.recvfrom(4096)
        try:
            signals = json.loads(data.decode('utf8'))
            signals['state'] = state.State(signals['state'])
        except json.JSONDecodeError as e:
            print('Could not decode {!r} : {}'.format(data, e))
    except socket.error as e:
        print(e)

    sphere_pixels = hp.animations.sphere(**signals)['value']
    # client.put_pixels(
    #     sphere_pixels[:512] * 255, channel=settings.sphere_channel1)
    # client.put_pixels(
    #     sphere_pixels[512:] * 255, channel=settings.sphere_channel2)

    for arm_config, arm in zip(settings.arm_configs, hp.animations.arms):
        arm_pixels = arm(**signals)['value']
        i = 0
        for offsets in arm_config.offsets:
            for offset in offsets:
                all_arm_pixels[
                    arm_config.channel][offset: offset + 64, :] = (
                        arm_pixels[i * 64: (i + 1) * 64])
                i += 1
        # TODO dirty hack!
        all_arm_pixels[4][0: 2 * 64] = all_arm_pixels[3][8 * 64:]
    for channel, pixels in all_arm_pixels.items():
        # client.put_pixels(pixels[:8 * 64] * 255, channel=channel)
        pass

    # beamz = hp.animations.beamz(**signals)['value']
    # pixels = (beamz * np.ones(shape=(512, 3)) * 255 * beamz)
    # client.put_pixels(pixels, channel=settings.enttec_channel)
    # if beamz > 0:
    #     print(pixels.shape, pixels.dtype, pixels[:10])
