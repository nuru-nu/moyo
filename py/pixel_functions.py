import os, sys
import json
import numpy as np
import colorsys
from scipy.stats import multivariate_normal
import time

nr_pixels = 10*60

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

def gaussian_droplet(mapping, pos, sigma, color):
	pixels = np.zeros((len(mapping), 3)) + np.array([color])

	kernel_max = multivariate_normal.pdf(pos, mean=pos, cov=sigma + 1.e-12)

	kernel = multivariate_normal.pdf(mapping, mean=pos, cov=sigma + 1.e-12)[:, np.newaxis]
	for coord_shift in [[-np.pi, 0], [np.pi, 0]]:
		kernel += multivariate_normal.pdf(mapping, mean=pos+np.array(coord_shift), cov=sigma + 1.e-12)[:, np.newaxis]
	
	return pixels*(kernel/kernel_max)