import bge
import socket
import os, sys
import io
import json
import numpy as np
import colorsys
from scipy.stats import multivariate_normal
import time

lib_path = bge.logic.expandPath("//../py/")
assert os.path.exists(lib_path), 'Make sure "." path is where notebooks are!'
if not lib_path in sys.path:
	sys.path.insert(0, lib_path)

import audio, features, settings, streaming, util
import pixel_functions as pf

def init(cont):
	own = cont.owner
	
	own['sock'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	own['sock'].settimeout(0)
	own['sock'].bind((settings.address, settings.fadecandy_port))

	own['drop_radius'] = np.pi/4
	own['drop_pos'] = np.array([0, 0])

	own['pixels'] = np.zeros((pf.nr_pixels, 3))
	own['polar_mapping'] = np.zeros((pf.nr_pixels, 2))
	own['speed'] = 60


	with open(bge.logic.expandPath("//../data/blender_polar.json")) as json_file:  
		data = json.load(json_file)
		for coord_data in data:
			idx = int(coord_data['idx'])
			phi = float(coord_data['phi'])
			theta = float(coord_data['theta'])
			own['polar_mapping'][idx-1] = np.array([phi, theta]) # phi: -pi - pi, theta 0 - pi
	
		print("Loaded pixels with shape:", own['polar_mapping'].shape)

	own['prev_t'] = time.time()

def run(cont):
	scene = bge.logic.getCurrentScene()
	own = cont.owner
	
	###################### Audio ##########################
	# try:
	# 	data, address = own['sock'].recvfrom(4096)
	# except io.BlockingIOError:
	# 	return False
	# try:
	# 	data = json.loads(data.decode('utf8'))
	# except json.JSONDecodeError as e:
	# 	print('Could not decode {!r} : {}'.format(data, e))
	# 	return False

	print(own['speed']*(time.time() - own['prev_t']))
	if own['speed']*(time.time() - own['prev_t']) > 60:
		own['prev_t'] = time.time()
		own['drop_pos'] = np.squeeze([np.random.rand(1)*np.pi, np.random.rand(1)*2*np.pi - np.pi])
		print(own['drop_pos'])

	

	pixels = pf.gaussian_droplet(own['polar_mapping'], own['drop_pos'], own['drop_radius'], [0,0,1], own['speed'])
	# pixels = pf.rotate_phi_ring(own['polar_mapping'], 4, [1,0,0], own['speed']) + pf.rotate_theta_ring(own['polar_mapping'], 4, [0,0,1], own['speed'])


	set_pixels(pixels)


def clear_pixels(cont):
	scene = bge.logic.getCurrentScene()
	own = cont.owner

	for i in range(pf.nr_pixels):
		scene.objects['pixel_' + str(i+1).zfill(3)].color = [0,0,0,1]

def set_pixels(pixels):
	scene = bge.logic.getCurrentScene()
	for idx, pix in enumerate(pixels):
		scene.objects['pixel_' + str(idx+1).zfill(3)].color = list(pix) + [1]