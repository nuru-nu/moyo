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

def init(cont):
	own = cont.owner
	
	own['sock'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	own['sock'].settimeout(0)
	own['sock'].bind((settings.address, settings.fadecandy_port))

	own['nr_pixels'] = 5*60
	own['drop_min_radius'] = np.pi/5
	own['drop_growth_rate'] = np.pi/100
	own['drop_max_radius'] = np.pi

	own['drop_radius'] = own['drop_min_radius']
	own['drop_pos'] = np.array([np.pi, np.pi/2])

	own['pixels'] = np.zeros((own['nr_pixels'], 3))
	own['polar_mapping'] = np.zeros((own['nr_pixels'], 2))


	with open(bge.logic.expandPath("//../data/blender_polar.json")) as json_file:  
		data = json.load(json_file)
		for coord_data in data:
			idx = int(coord_data['idx'])
			phi = float(coord_data['phi'])
			theta = float(coord_data['theta'])
			own['polar_mapping'][idx-1] = np.array([phi, theta])
	
		print("Loaded pixels with shape:", own['polar_mapping'].shape)

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

	kernel = multivariate_normal(own['drop_pos'], [[own['drop_radius'], 0], [0, own['drop_radius']]])

	pixels = rotate_phi_ring(own['polar_mapping'], 4, [1,0,0], 20) + rotate_theta_ring(own['polar_mapping'], 4, [1,0,0], 20)
	set_pixels(pixels)


	# for i in range(own['nr_pixels']):
	# 	coord = own['polar_coords'][i]
	# 	coord[2] = kernel.pdf(coord[0:2])
	# 	# r = coord[2]

	# 	# print(i, coord)
	# 	# r = own['drop_radius'] / np.pi
		
	# 	# r = (coord[0] + np.pi/2) / np.pi own['drop_radius']
	# 	r = np.clip((0.5*np.pi - width*np.abs(coord[0] + (own['drop_radius'] - (0.5*np.pi)))), 0, 0.5*np.pi) / (0.5*np.pi)

	# 	# print(r, np.clip((0.5*np.pi - width*np.abs(coord[0])), 0, 0.5*np.pi) / (0.5*np.pi), 
	# 	#          np.clip((0.5*np.pi - width*np.abs(coord[0])), 0, 0.5*np.pi), "/", 0.5*np.pi)

	# 	scene.objects['pixel_' + str(i+1).zfill(3)].color = [r, g, b, a]

def clear_pixels(cont):
	scene = bge.logic.getCurrentScene()
	own = cont.owner

	for i in range(own['nr_pixels']):
		scene.objects['pixel_' + str(i+1).zfill(3)].color = [0,0,0,1]

def set_pixels(pixels):
	scene = bge.logic.getCurrentScene()
	for idx, pix in enumerate(pixels):
		scene.objects['pixel_' + str(idx+1).zfill(3)].color = list(pix) + [1]

def rotate_theta_ring(mapping, width, color, speed):
	pixels = np.zeros((len(mapping), 3))

	for i in range(len(pixels)):
		coord = mapping[i]

		rad_pos = np.pi * ((speed*time.time() % 60) / 60.0)

		I = np.clip((0.5*np.pi - width*np.abs(coord[1] + (rad_pos - np.pi))), 0, 0.5*np.pi) / (0.5*np.pi)

		pixels[i] = I*np.array(color)

	return pixels

def rotate_phi_ring(mapping, width, color, speed):
	pixels = np.zeros((len(mapping), 3))

	for i in range(len(pixels)):
		coord = mapping[i]

		rad_pos = 2 * np.pi * ((speed*time.time() % 60) / 60.0)

		I = np.clip((np.pi - width*np.abs(coord[0] + (rad_pos - (np.pi)))), 0, np.pi) / (np.pi)

		pixels[i] = I*np.array(color)

	return pixels