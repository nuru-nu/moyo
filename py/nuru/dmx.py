"""DMX effector.

Prerequisites : OLA & DMX USB Pro

- Buy https://www.enttec.com/eu/products/controls/dmx-usb/dmx-usb-pro/
- Install OLA
  Ubuntu:
  sudo apt-get install -y ola-python ola
  OS X:
  brew install ola
  http://www.ftdichip.com/Drivers/VCP/MacOSX/FTDIUSBSerialDriver_v2_4_2.dmg
  sudo kextload -b com.apple.driver.AppleUSBFTDI
  ls -lh /dev/tty.usbserial-EN237452
- Correct configuration
  https://www.openlighting.org/ola/getting-started/device-specific-configuration/#Enttec_USB_Pro
  echo > ~/.ola/ola-usbpro.conf <<EOC
  device_dir = /dev
  device_prefix = tty.usbserial-
  EOC
- checks logs
  linux : grep olad /var/log/syslog
  linux : dmesg
- Start server:
  OS X : olad -l 2
  linux : sudo /etc/init.d/olad restart
  http://localhost:9090/ola.html
"""

import sys

import numpy as np

from smanmi import dmx_devices, hotplug, network, util
from . import settings


# dirty hack to fix includes
paths = [
    '/usr/local/Cellar/ola/0.10.6/lib/python2.7/site-packages',
    '/usr/lib/python2.7/dist-packages/'
]
for path in paths:
    if path not in sys.path:
        sys.path.append(path)
from ola.ClientWrapper import ClientWrapper  # NOQA


# stage1 = dmx_devices.StageLight()
# stage1.intensity = 255
# stage2 = dmx_devices.StageLight()
# stage2.intensity = 255
# stage1.green = 255
# dmx_controller.add_device(stage1, universe=1, channel_offset=0)
# dmx_controller.add_device(stage2, universe=1, channel_offset=4)

zbeam = dmx_devices.ZBeam()
zbeam.volume = 0

dmx_controller = dmx_devices.DmxController(wrapper=ClientWrapper())
dmx_controller.add_device(zbeam, universe=0, channel_offset=0)

dmx_controller.update()

if __name__ == '__main__':

    logger = util.createLogger('dmx')
    sock = network.create_udp_socket(
        settings.dmx_port, settings.address, timeout=None)

    effects = hotplug.HotPlug('.hotplug.effects', logger)
    status_sender = network.StatusSender(name='dmx', logger=logger)

    beamz_volumes = np.zeros(int(10 / settings.hop_secs))
    loop_i = 0
    while True:
        signals = network.get_json(sock, {})

        # stage1.red = int(data.get('low', 0) * 255)
        # stage1.blue = int(data.get('high', 0) * 255)
        # stage2.blue = int(data.get('low', 0) * 255)
        # stage2.red = int(data.get('high', 0) * 255)

        zbeam.volume = int(effects.beamz(**signals)['value'] * 255)
        if zbeam.volume:
            logger.info(zbeam.volume)

        dmx_controller.update()

        beamz_volumes[loop_i % len(beamz_volumes)] = zbeam.volume
        loop_i += 1
        status_sender.send('beamz_volume={}'.format(beamz_volumes.mean()))
