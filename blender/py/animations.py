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

import audio, features, settings, util
import pixel_functions as pf

def init(cont):
	own = cont.owner
	
	own['sock'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	own['sock'].settimeout(0)
	own['sock'].bind((settings.address, settings.fadecandy_port))

	own['pixels'] = np.zeros((pf.nr_pixels, 3))
	own['polar_mapping'] = np.zeros((pf.nr_pixels, 2))

	own['max_time'] = 9000000 # 2500 hours
	own['reset_time'] = time.time() % own['max_time']

	# Animation Variables
	own['speed'] = 1
	own['anim_durtion'] = 1
	own['drop_radius'] = np.pi/16
	own['drop_pos'] = np.array([0.0, np.pi/2])
	own['color'] = [0,0,1]



	with open(bge.logic.expandPath("//../data/blender_polar.json")) as json_file:  
		data = json.load(json_file)
		for coord_data in data:
			idx = int(coord_data['idx'])
			phi = float(coord_data['phi'])
			theta = float(coord_data['theta'])
			own['polar_mapping'][idx-1] = np.array([phi, theta]) # phi: -pi - pi, theta 0 - pi
	
		print("Loaded pixels with shape:", own['polar_mapping'].shape)

	own['prev_t'] = time.time() % 120

def run(cont):
	scene = bge.logic.getCurrentScene()
	own = cont.owner
	
	# ##################### Audio ##########################
	# try:
	# 	data, address = own['sock'].recvfrom(4096)
	# except io.BlockingIOError:
	# 	return False
	# try:
	# 	data = json.loads(data.decode('utf8'))
	# except json.JSONDecodeError as e:
	# 	print('Could not decode {!r} : {}'.format(data, e))
	# 	return False

	t_global = time.time() % own['max_time']

	# if t_global - own['reset_time'] > own['anim_durtion']:
	# 	own['reset_time'] = t_global
	# 	own['drop_pos'] = np.squeeze([np.random.rand(1)*np.pi, np.random.rand(1)*2*np.pi - np.pi])

	t_anim = t_global - own['reset_time']

	# print(t_anim, own['drop_pos'])
	# sigma = ((np.sin(own['speed']*2*t_anim*np.pi) + 1)/2)*own['drop_radius']
	sigma = (t_anim / own['anim_durtion'])*own['drop_radius']

	if sigma > own['drop_radius']:
		own['reset_time'] = t_global
		own['drop_pos'] = np.squeeze([np.random.rand(1)*np.pi, np.random.rand(1)*2*np.pi - np.pi])
		own['color'] = [np.random.rand(), np.random.rand(), np.random.rand()]

	pixels = pf.gaussian_droplet(own['polar_mapping'], own['drop_pos'], sigma, own['color'])
	set_pixels(pixels)

	# time.sleep(0.1)

def clear_pixels(cont):
	scene = bge.logic.getCurrentScene()
	own = cont.owner

	for i in range(pf.nr_pixels):
		scene.objects['pixel_' + str(i+1).zfill(3)].color = [0,0,0,1]

def set_pixels(pixels):
	scene = bge.logic.getCurrentScene()
	for idx, pix in enumerate(pixels):
		scene.objects['pixel_' + str(idx+1).zfill(3)].color = list(pix) + [1]