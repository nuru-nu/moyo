# vim: set noet:ts=8:sw=8
# flake8: noqa

import opc
import time
import numpy as np
import socket
import io
import json

import colorsys

import audio, features, settings, state, util
import pixel_functions as pf
import hotplug

fc_channels = {'rizhole' : 1, 'vine_1' : 2}

logger = util.createLogger('fadecandy')
hp = hotplug.HotPlug(logger, modules=('animations',))

client = opc.Client('localhost:7890')
client.set_interpolation(False)

max_t = 9000000 # 2500 hours

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

sock.settimeout(None)
sock.bind((settings.address, settings.fadecandy_port))

signals = {"t" : time.time(), "loud" : np.random.rand(1)[0], "pitch" : np.random.rand(1)[0], "ooo": 0}

arm_channels = set(arm_config.channel for arm_config in settings.arm_configs)
all_arm_pixels = {
    channel: np.zeros([8*64, 3])
    for channel in arm_channels
}

last_t = 0
while True:
	##################### Audio ##########################
	try:
		data, address = sock.recvfrom(4096)
		try:
			signals = json.loads(data.decode('utf8'))
			signals['state'] = state.State(signals['state'])
		except json.JSONDecodeError as e:
			print('Could not decode {!r} : {}'.format(data, e))
	except io.BlockingIOError as e:
		print(e)

	# if time.time() - last_t > 1:
	# 	print(signals)
	# 	last_t = time.time()
	
	# signals["rand"] = np.random.rand(1)[0]
	# signals["vol"] = signals['tf']
	# pixels = hp.animations.animation(signals)

	sphere_pixels = hp.animations.sphere(**signals)['value']
	client.put_pixels(sphere_pixels[:512]*255, channel=settings.sphere_channel1)
	client.put_pixels(sphere_pixels[512:]*255, channel=settings.sphere_channel2)

	for arm_config, arm in zip(settings.arm_configs, hp.animations.arms):
		arm_pixels = arm(**signals)['value']
		i = 0
		for offsets in arm_config.offsets:
			for offset in offsets:
				all_arm_pixels[arm_config.channel][offset: offset+64, :] = (
					arm_pixels[i * 64: (i + 1) * 64])
				i += 1
	for channel, pixels in all_arm_pixels.items():
		client.put_pixels(pixels*255, channel=channel)

