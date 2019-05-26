# vim: set noet:ts=8:sw=8
# flake8: noqa

import numpy as np
import os
import json
from pathlib import Path
import time
import colorsys

import pixel_functions as pf, settings, util

max_time = 9000000 # 2500 hours
mapping = np.zeros((settings.sphere_pixels,2))

# for file in Path('git/rizhom/data/blender_polar.json').exists():
# 	print(file)

root = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')
json_path = os.path.join(root, 'data', 'blender_polar.json')

if Path("../data/rec_2_polar.json").exists():
	with open("../data/rec_2_polar.json") as json_file: 
		data = json.load(json_file)
		for coord_data in data:
			idx = int(coord_data['idx'])
			phi = float(coord_data['phi'])
			theta = float(coord_data['theta'])
			mapping[idx-1] = np.array([phi, theta]) # phi: -pi - pi, theta 0 - pi
elif Path(json_path).exists():
	with open(json_path) as json_file: 
		data = json.load(json_file)
		for coord_data in data:
			idx = int(coord_data['idx'])
			phi = float(coord_data['phi'])
			theta = float(coord_data['theta'])
			mapping[idx-1] = np.array([phi, theta]) # phi: -pi - pi, theta 0 - pi
else:
	print("Cant find mapping JSON '{}'!".format(json_path))


def full_on(color, nr_pixels):
	return np.tile(color, nr_pixels).reshape(nr_pixels, -1)


class Mixer:

	def __init__(self, d):
		self.d = d
		self.t0 = 0
		self.dt = 1
		self.current = self.last = 'std'

	def __call__(self, signals):
		state = signals['state'].state
		t = signals['t']
		if state != self.current:
			self.last = self.current
			self.current = state
			self.t0 = t
		if t - self.t0 < self.dt:
			v = (t - self.t0) / self.dt
			return (1 - v) * self.d[self.last](signals) + v * self.d[state](signals)
		return self.d[state](signals)


class Animation:
	def __init__(self):
		self.pixels = np.zeros((len(mapping), 3))

	def __call__(self, signals):
		pass

	def __or__(self, other):
		return ChainedAnimation(self, other)


class ChainedAnimation(Animation):
	def __init__(self, animation1, animation2):
		self.animation1 = animation1
		self.animation2 = animation2

	def __call__(self, x):
		return self.animation2(self.animation1(x))


class Signals(Animation):
	def __init__(self, name):
		self.name = name

	def __call__(self, signals):
		return signals[self.name]


class Const(Animation):
	def __init__(self, value):
		self.value = value

	def __call__(self, x):
		return self.value


class Rand(Animation):
	def __init__(self, rand_range):
		self.value =  rand_range[0] + (rand_range[1] - rand_range[0])*np.random.rand(1)[0]

	def __call__(self, x):
		return self.value


class Sin(Animation):
	def __init__(self, hz):
		self.hz = hz

	def __call__(self, x):
		return np.sin(x * 2 * np.pi * self.hz)


class OooHue:
	def __call__(self, signals):
		return 0.5 + 0.5 * np.sin(signals['t'] * 2 * np.pi * (
			0.02  # + 0.01 * np.clip(signals['ooo_intensity'], 0, 1)
			))


class Lin(Animation):
	def __init__(self, shift=0, mult=1):
		self.shift = shift
		self.mult = mult

	def __call__(self, x):
		return self.shift + x*self.mult


class ThetaRing(Animation):
	def __init__(self, width, color, pos):
		self.width = width
		self.color = color
		self.pos = pos

	def __call__(self, signals):
		I = np.clip((0.5*np.pi - self.width(signals)*np.abs(mapping[:,1] + (self.pos(signals) - np.pi))), 0, 0.5*np.pi) / (0.5*np.pi)
		return np.repeat(np.expand_dims([col(signals) for col in self.color], axis=0), len(mapping), axis=0)*np.expand_dims(I, axis=1)


class GaussianDroplet(Animation):
	def __init__(self, sigma, color, pos):
		self.sigma = sigma
		self.color = color
		self.pos = pos

	def __call__(self, signals):
		return pf.gaussian_droplet(mapping, [p(signals) for p in self.pos], self.sigma(signals), [col(signals) for col in self.color]) 


class GaussianRain(Animation):
	def __init__(self, nr_droplets, radius, drop_duration, color):
		self.radius = radius
		self.nr_droplets = nr_droplets
		self.drop_duration = drop_duration
		self.color = color
		self.t_0s = [time.time() + 5*np.random.rand(1)[0] for _ in range(int(self.nr_droplets))]
		self.positions = [[pf.rand_range((-np.pi, np.pi)), pf.rand_range((0, np.pi))] for _ in range(int(self.nr_droplets))]
		self.colors = [[0, 0, 0] for _ in range(int(self.nr_droplets))]

	def __call__(self, signals):
		pixels = np.zeros((len(mapping), 3))
		for drop_nr in range(self.nr_droplets):
			if (time.time() - self.t_0s[drop_nr]) / self.drop_duration(signals) > 1:
				self.t_0s[drop_nr] = time.time()
				phi, theta = util.phi_theta_samples(1)
				self.positions[drop_nr] = [phi[0] - np.pi, 2*theta[0]]
				# self.positions[drop_nr] = [pf.rand_range((-np.pi, np.pi)), pf.rand_range((0, np.pi))]
				self.colors[drop_nr] = [col(signals) for col in self.color]

			sigma = self.radius(signals) * (time.time() - self.t_0s[drop_nr]) / self.drop_duration(signals)

			pixels += pf.gaussian_droplet(mapping, self.positions[drop_nr], sigma, self.colors[drop_nr])

		return pixels 


class Hue(Animation):
	def __init__(self, hue=Const(1), saturation=Const(1), value=Const(1)):
		self.hue = hue
		self.saturation = saturation
		self.value = value

	def __call__(self, signals):
		return colorsys.hsv_to_rgb(
			self.hue(signals),
			self.saturation(signals),
			self.value(signals))


class FullOn(Animation):
	def __init__(self, color):
		self.color = color

	def __call__(self, signals):
		return full_on(self.color(signals), settings.sphere_pixels)


class ThetaRing(Animation):
	def __init__(self, phi, width, color):
		self.phi = phi
		self.width = width
		self.color = color

	def __call__(self, signals):
		return pf.theta_ring(
			mapping,
			phi=self.phi(signals),
			width=self.width(signals),
			color=self.color(signals),
		)


class PhiRing(Animation):
	def __init__(self, theta, width, color):
		self.theta = theta
		self.width = width
		self.color = color

	def __call__(self, signals):
		return pf.phi_ring(
			mapping,
			theta=self.theta(signals),
			width=self.width(signals),
			color=self.color(signals),
		)

class Add(Animation):
	def __init__(self, *anims):
		self.anims = anims
	def __call__(self, signals):
		pixels = self.anims[0](signals)
		for anim in self.anims[1:]:
			pixels += anim(signals)
		return pixels

# arms
###############################################################################


def or_const(x):
	def wrapper(signals):
		return x
	return x if isinstance(x, Animation) else wrapper


class ArmFullOn(Animation):
	def __init__(self, arm_config, color, mult=1):
		self.arm_config = arm_config
		self.color = or_const(color)
		self.mult = or_const(mult)
	def __call__(self, signals):
		color = self.color(signals)
		return np.concatenate([
			full_on(color, 64)
			for offsets in self.arm_config.offsets
			for offset in offsets
		]) * self.mult(signals)


class ArmGradient(ArmFullOn):
	def __init__(self, arm_config, color, func, mult=1):
		"""Func is a scalar function mapping 0..1 to a value."""
		super().__init__(arm_config, color, mult)
		self.func = func
	def __call__(self, signals):
		pixels = super().__call__(signals)
		dist = np.concatenate([
			np.tile(np.concatenate([
				np.linspace(meter, meter + 1, 60) / len(self.arm_config.offsets),
				[0.0] * 4,
			]), len(offsets))
			for meter, offsets in enumerate(
				self.arm_config.offsets)
		])
		return np.array([
			pixel * self.func(d)
			for d, pixel in zip(dist, pixels)
		])
