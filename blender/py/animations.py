import bge
import socket
import os, sys
import io
import json
import numpy as np
import colorsys
from scipy.stats import multivariate_normal

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
	own['init_drop_radius'] = np.pi/5
	own['drop_growth_rate'] = np.pi/50
	own['drop_max_radius'] = np.pi

	own['drop_radius'] = own['init_drop_radius']
	own['drop_pos'] = np.array([np.pi, np.pi/2])

	scene = bge.logic.getCurrentScene()

	with open(bge.logic.expandPath("//../data/blender_polar.json")) as json_file:  
		data = json.load(json_file)
		own['polar_coords'] = [None]*len(data)
		own['polar_coords'][0] = (0,0)
		for coord_data in data:
			idx = int(coord_data['idx'])
			phi = float(coord_data['phi'])
			theta = float(coord_data['theta'])
			own['polar_coords'][idx - 1] = [phi, theta, 0]		# phi(0 - 2pi), theta(0 - pi), intensity (0 - 1)
		own['polar_coords'] = np.array(own['polar_coords'])
		print("Loaded pixels with shape:", own['polar_coords'].shape)


def run(cont):
	scene = bge.logic.getCurrentScene()
	own = cont.owner
	
	# try:
	# 	data, address = own['sock'].recvfrom(4096)
	# except io.BlockingIOError:
	# 	return False
	# try:
	# 	data = json.loads(data.decode('utf8'))
	# except json.JSONDecodeError as e:
	# 	print('Could not decode {!r} : {}'.format(data, e))
	# 	return False

	# r, g, b = colorsys.hsv_to_rgb(np.clip(data['pitch']  / 400, 0, 1), 1, np.clip(data['loud']  / 0.25, 0, 1))
	# a = 1.0
	r, g, b, a = [0,0,0,1]

	own['drop_radius'] += own['drop_growth_rate']
	if own['drop_radius'] > own['drop_max_radius']:
		own['drop_radius'] = own['init_drop_radius']
	# own['drop_radius'] = np.pi

	kernel = multivariate_normal(own['drop_pos'], [[own['drop_radius'], 0], [0, own['drop_radius']]])

	for i in range(own['nr_pixels']):
		coord = own['polar_coords'][i]
		coord[2] = kernel.pdf(coord[0:2])
		# r = coord[2]

		# print(i, coord)
		# r = own['drop_radius'] / np.pi
		
		# r = (coord[0] + np.pi/2) / np.pi own['drop_radius']
		r = coord[1] / np.pi # np.pi own['drop_radius']


		scene.objects['pixel_' + str(i+1).zfill(3)].color = [r, g, b, a]
