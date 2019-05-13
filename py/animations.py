import numpy as np
import pixel_functions as pf
import json
from pathlib import Path
import time
import util

nr_pixels = 600
max_time = 9000000 # 2500 hours
mapping = np.zeros((nr_pixels,2))

# for file in Path('git/rizhom/data/blender_polar.json').exists():
# 	print(file)

if Path('git/rizhom/data/blender_polar.json').exists():
	with open('git/rizhom/data/blender_polar.json') as json_file: 
		data = json.load(json_file)
		for coord_data in data:
			idx = int(coord_data['idx'])
			phi = float(coord_data['phi'])
			theta = float(coord_data['theta'])
			mapping[idx-1] = np.array([phi, theta]) # phi: -pi - pi, theta 0 - pi
else:
	print("Cant find mapping JSON!")

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
		self.t_0s = [time.time() % max_time + np.random.rand(1)[0] for _ in range(int(self.nr_droplets))]
		self.positions = [[pf.rand_range((-np.pi, np.pi)), pf.rand_range((0, np.pi))] for _ in range(int(self.nr_droplets))]
		self.colors = [[0, 0, 0] for _ in range(int(self.nr_droplets))]

	def __call__(self, signals):
		pixels = np.zeros((len(mapping), 3))
		for drop_nr in range(self.nr_droplets):
			if (time.time() % max_time - self.t_0s[drop_nr]) / self.drop_duration(signals) > 1:
				self.t_0s[drop_nr] = time.time() % max_time
				phi, theta = util.phi_theta_samples(1)
				self.positions[drop_nr] = [phi[0] - np.pi, 2*theta[0]]
				# self.positions[drop_nr] = [pf.rand_range((-np.pi, np.pi)), pf.rand_range((0, np.pi))]
				self.colors[drop_nr] = [col(signals) for col in self.color]

			sigma = self.radius(signals) * (time.time() % max_time - self.t_0s[drop_nr]) / self.drop_duration(signals)

			pixels += pf.gaussian_droplet(mapping, self.positions[drop_nr], sigma, self.colors[drop_nr])

		return pixels 
