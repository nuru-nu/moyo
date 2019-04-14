import bge
import socket
import os, sys
import io
import json
import numpy as np
import colorsys

lib_path = bge.logic.expandPath("//../py/")
assert os.path.exists(lib_path), 'Make sure "." path is where notebooks are!'
if not lib_path in sys.path:
	sys.path.insert(0, lib_path)

import audio, features, settings, streaming, util

def init(cont):
	own = cont.owner
	
	own['sock'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	own['sock'].settimeout(0)
	own['sock'].bind((settings.address, settings.fadecandy_port))

	own['nr_pixels'] = 5*60

	scene = bge.logic.getCurrentScene()

def run(cont):
	scene = bge.logic.getCurrentScene()
	own = cont.owner
	
	try:
		data, address = own['sock'].recvfrom(4096)
	except io.BlockingIOError:
		return False
	try:
		data = json.loads(data.decode('utf8'))
	except json.JSONDecodeError as e:
		print('Could not decode {!r} : {}'.format(data, e))
		return False

	r, g, b = colorsys.hsv_to_rgb(np.clip(data['pitch']  / 400, 0, 1), 1, np.clip(data['loud']  / 0.25, 0, 1))
	a = 1.0

	for i in range(own['nr_pixels']):
		scene.objects['pixel_' + str(i+1).zfill(3)].color = [r, g, b, a]