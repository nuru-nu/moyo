import opc
import time
import numpy as np
import socket
import io
import json

import colorsys

import audio, features, settings, state, util
import pixel_functions as pf
# import animation_script as anim
import hotplug

logger = util.createLogger('fadecandy')
hp = hotplug.HotPlug(logger)

numLEDs = 512
client = opc.Client('localhost:7890')
client.set_interpolation(False)

max_t = 9000000 # 2500 hours

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

sock.settimeout(None)
sock.bind((settings.address, settings.fadecandy_port))

signals = {"t" : time.time(), "loud" : np.random.rand(1)[0], "pitch" : np.random.rand(1)[0], "ooo": 0}

last_t = 0
while True:
	##################### Audio ##########################
	try:
		data, address = sock.recvfrom(4096)
		try:
			signals = json.loads(data.decode('utf8'))
                        signals['state'] = state.Stage(signals['state'])
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

	pixels = hp.animations.animation(signals)
	# pixels = anim.get_pixels(signals, 'uniform_rain')
	# print(pixels)
	client.put_pixels(pixels*255)
