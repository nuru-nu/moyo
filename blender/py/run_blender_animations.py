# vim: set noet:ts=8:sw=8
# flake8: noqa
import sys

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
data_path = bge.logic.expandPath("//../data/")
assert os.path.exists(lib_path), 'Make sure "." path is where notebooks are!'
if not lib_path in sys.path:
	sys.path.insert(0, lib_path)

import audio, features, settings, state, util
import pixel_functions as pf
# import animation_script as anim
import hotplug

logger = util.createLogger('fadecandy')
hp = hotplug.HotPlug(logger, modules=('animations',))

# signals0 = {"vol" : np.random.rand(1)[0], "pitch" : np.random.rand(1)[0], "rand" : np.random.rand(1)[0], "state": state.State()}
signals0 = {"t" : time.time(), "loud" : np.random.rand(1)[0], "pitch" : np.random.rand(1)[0], "ooo": 0}

def init(cont):
	own = cont.owner
	
	own['sock'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	own['sock'].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

	own['sock'].settimeout(0)
	own['sock'].bind((settings.address, settings.fadecandy_port))

	own['pixels'] = np.zeros((settings.sphere_pixels, 3))
	own['polar_mapping'] = np.zeros((settings.sphere_pixels, 2))

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
	own['signals'] = signals0

	arm_channels = set(arm_config.channel for arm_config in settings.blender_arm_configs)
	own['all_arm_pixels'] = {
	    channel: np.zeros([120, 3])
	    for channel in arm_channels
	}


def run(cont):
	global signals
	scene = bge.logic.getCurrentScene()
	own = cont.owner
	
	# ##################### Audio ##########################

	signals = own.get('signals', signals0)
	try:
		data, address = own['sock'].recvfrom(4096)
		try:
			signals = own['signals'] = json.loads(data.decode('utf8'))
			signals['state'] = state.State(signals['state'])
		except json.JSONDecodeError as e:
			print('Could not decode {!r} : {}'.format(data, e))
	except io.BlockingIOError as e:
		pass

	sphere_pixels = hp.animations.sphere(**signals)['value']

	set_pixels(sphere_pixels, 'pixel_', 1)

	for arm_config, arm in zip(settings.blender_arm_configs, hp.animations.arms):
		arm_pixels = arm(**signals)['value']
		i = 0
		for offsets in arm_config.offsets:
			for offset in offsets:
				set_pixels(arm_pixels[i * 64: (i + 1) * 64][:60], arm_config.channel, 1 + offset)
				i += 1

def set_pixels(pixels, prefix, sdx):
	scene = bge.logic.getCurrentScene()
	for idx, pix in enumerate(pixels):
		scene.objects[prefix + str(idx+sdx).zfill(3)].color = list(pix) + [1]
