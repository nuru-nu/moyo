# vim: set noet:ts=8:sw=8
# flake8: noqa

import os, sys
import json
import numpy as np
import colorsys
from scipy.stats import multivariate_normal
import time


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

	dist_mapping = dist_pos(haversine(np.repeat(pos[0], len(mapping)), np.repeat(pos[1], len(mapping)), mapping[:,0], mapping[:,1], 1),
							 bearing(np.repeat(pos[0], len(mapping)), np.repeat(pos[1], len(mapping)), mapping[:,0], mapping[:,1]))
	

	kernel = multivariate_normal.pdf(dist_mapping, mean=[0,0], cov=np.abs(sigma) + 1.e-12)[:, np.newaxis]
	
	return pixels*kernel

def subtract(a, b, period):
    """Calculates (a-b) within periodicity `period`."""
    if a < b:
        while a + period/2 < b:
            a += period
    else:
        while a > b + period/2:
            b += period
    return a - b

def haversine(phi1, theta1, phi2, theta2, radius):
    """
    Calculate the great circle distance between two points in radians
    """
    t1 = theta1 - np.pi/2
    t2 = theta2 - np.pi/2

    # haversine formula 
    dphi = phi2 - phi1 
    dtheta = t2 - t1 
    a = np.sin(dtheta/2)**2 + np.cos(t1) * np.cos(t2) * np.sin(dphi/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    return radius * c

def bearing(phi1, theta1, phi2, theta2):
	t1 = theta1 - np.pi/2
	t2 = theta2 - np.pi/2

	X = np.cos(t2) * np.sin(np.abs(phi1-phi2))
	Y = np.cos(t1) * np.sin(t2) - np.sin(t1) * np.cos(t2) * np.cos(np.abs(phi1-phi2))
	return np.arctan2(X,Y)

def dist_pos(d, theta):
    theta_rad = np.pi/2 - theta
    return np.concatenate((np.expand_dims(d*np.cos(theta_rad),axis=1), np.expand_dims(d*np.sin(theta_rad),axis=1)),axis=1)

def rand_range(rand_range):
	return rand_range[0] + (rand_range[1] - rand_range[0])*np.random.rand(1)[0]


# def cos_(x):
#     """Maps 0..1 to 0..1 with cos() non-linearity."""
#     return (1+np.cos((np.clip(x, 0, 1)-1)*np.pi))/2

def theta_ring(mapping, phi, width, color):
	"""Lights all pixels at phi+/-width."""
	pixels = np.zeros((len(mapping), 3))

	for i in range(len(pixels)):
		coord = mapping[i]
		dist = np.abs((phi % (2*np.pi) - np.pi) - coord[0])
		I = 1 - np.clip(dist / width, 0, 1)
		pixels[i] = I*np.array(color)

	return pixels

def phi_ring(mapping, theta, width, color):
	"""Lights all pixels at theta+/-width."""
	pixels = np.zeros((len(mapping), 3))
	# theta = np.pi - theta

	for i in range(len(pixels)):
		coord = mapping[i]
		# coord == [phi, theta]
		dist = np.abs(((theta * 1.2) % (2*np.pi)) - coord[1])
		I = 1 - np.clip(dist / width, 0, 1)
		pixels[i] = I*np.array(color)

	return pixels
