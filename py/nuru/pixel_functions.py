# flake8: noqa

import json, os, sys, time

import numpy as np
from scipy.stats import multivariate_normal, norm


def spherical_gaussian_droplet(phi_r_mapping, pos, sigma, color):
        pixels = np.zeros((len(phi_r_mapping), 3)) + np.array([color])
        phi0, r0 = pos
        n, (phi, r) = len(phi_r_mapping), phi_r_mapping.T

        dist_mapping = dist_pos(
            haversine(
                phi1=np.repeat(phi0, n),
                theta1=np.repeat(r0, n),
                phi2=phi,
                theta2=r,
                radius=1),
            bearing(
                phi1=np.repeat(phi0, n),
                theta1=np.repeat(r0, n),
                phi2=phi,
                theta2=r),
        )

        kernel = multivariate_normal.pdf(
            dist_mapping, mean=[0,0], cov=np.abs(sigma) + 1.e-12
        )[:, np.newaxis]

        return pixels * kernel


def r_phi_gaussian_1d(phi_r_mapping, pos, sigma, color):
    """Distance is take in (x, y) space defined by phi_r_mapping."""
    (phi, r), (phi0, r0) = phi_r_mapping.T, pos
    dist = (
        (r * np.cos(phi) - r0 * np.cos(phi0)) ** 2 +
        (r * np.sin(phi) - r0 * np.sin(phi0)) ** 2
    ) ** .5
    return norm.pdf(dist, scale=sigma)[:, np.newaxis] * [color]


def haversine(phi1, theta1, phi2, theta2, radius):
    """
    Calculate the great circle distance between two points in radians.
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
    theta_rad = np.pi / 2 - theta
    return np.concatenate(
        (
            np.expand_dims(d * np.cos(theta_rad),axis=1),
            np.expand_dims(d * np.sin(theta_rad),axis=1),
        ),
        axis=1)


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

