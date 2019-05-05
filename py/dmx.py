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
- Start server:
  OS X : olad -l 2
  http://localhost:9090/ola.html
"""

import collections, json, socket, sys

import array
import numpy as np

import settings, util


# dirty hack to fix includes
paths = [
    '/usr/local/Cellar/ola/0.10.6/lib/python2.7/site-packages',
    '/usr/lib/python2.7/dist-packages/'
]
for path in paths:
    if path not in sys.path:
        sys.path.append(path)
from ola.ClientWrapper import ClientWrapper  # NOQA


class DmxDevice:
    """Defines a property -> channel mapping (0 based)."""

    def __init__(self):
        self.init_data()
        assert type(self.data) == collections.OrderedDict

    def init_data(self):
        self.data = collections.OrderedDict()

    def __dir__(self):
        return self.data.keys()

    def __getattr__(self, k):
        return self.data[k]

    def __setattr__(self, k, v):
        if k == 'data':
            return super().__setattr__(k, v)
        assert k in self.data
        self.data[k] = v

    def values(self):
        return list(self.data.values())

    def __len__(self):
        return len(self.data)


class FroggyLight(DmxDevice):
    def init_data(self):
        self.data = collections.OrderedDict([
            ('dimmer', 0),
            ('strobe', 0),
            ('red', 0),
            ('green', 0),
            ('blue', 0),
            #  pan : 0=148: 0
            #        37=184: pi/2
            #        72=221: pi
            #        109=255: 3pi/2
            ('pan', 0),
            #  tilt: 38: 0
            #        86: pi/4
            #        133: pi/2
            #        191: 3pi/4
            #        229: pi
            ('tilt', 0),
            ('speed', 0),
        ])


class StageLight(DmxDevice):
    def init_data(self):
        self.data = collections.OrderedDict([
            ('intensity', 0),
            ('red', 0),
            ('green', 0),
            ('blue', 0),
        ])


class DmxController:
    """Maps multiple DmxDevice to a controller."""

    def __init__(self):
        self.devices = []
        self.universes = []
        self.channel_offsets = []
        self.universe_sizes = {}
        self.wrapper = ClientWrapper()
        self.client = self.wrapper.Client()
        self.lastas = {}

    def add_device(self, device, universe, channel_offset=0):
        self.devices.append(device)
        self.universes.append(universe)
        self.channel_offsets.append(channel_offset)
        self.universe_sizes[universe] = max(
            self.universe_sizes.get(universe, 0), channel_offset + len(device)
        )

    def pad_universe_size(self, universe_size):
        return int(np.ceil(universe_size / 16) * 16)

    def values(self):
        values = {
            universe: np.zeros(
                self.pad_universe_size(universe_size), dtype=np.uint8)
            for universe, universe_size in self.universe_sizes.items()
        }
        for device, universe, offset in zip(
            self.devices,
            self.universes,
            self.channel_offsets
        ):
            values[universe][
                offset: offset + len(device)] = device.values()
        return values

    def update(self):
        for universe, values in self.values().items():
            a = array.array('B', map(int, values))
            if self.lastas.get(universe) == a:
                continue
            self.client.SendDmx(universe, a, lambda state: self.wrapper.Stop())


logger = util.createLogger('dmx')

stage1 = StageLight()
stage1.intensity = 255
stage2 = StageLight()
stage2.intensity = 255
# stage1.green = 255
dmx_controller = DmxController()
dmx_controller.add_device(stage1, universe=1, channel_offset=0)
dmx_controller.add_device(stage2, universe=1, channel_offset=4)

dmx_controller.update()

if __name__ == '__main__':

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.settimeout(None)
    sock.bind((settings.address, settings.dmx_port))

    while True:
        data, address = sock.recvfrom(4096)
        data = json.loads(data.decode("utf8"))

        stage1.red = int(data.get('low', 0) * 255)
        stage1.blue = int(data.get('high', 0) * 255)
        stage2.blue = int(data.get('low', 0) * 255)
        stage2.red = int(data.get('high', 0) * 255)

        dmx_controller.update()
