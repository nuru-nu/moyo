import bpy
import bpy_functions as bf
import numpy as np
import os.path, sys
import json
import math as m

lib_path = bpy.path.abspath("//../py/")
assert os.path.exists(lib_path), 'Make sure "." path is where notebooks are!'
if not lib_path in sys.path:
    sys.path.insert(0, lib_path)

import audio, features, settings, streaming, util

sphere = bpy.data.objects['Sphere']
nr_verts = len(sphere.data.vertices)
nr_pixels = 5*60

radius = np.linalg.norm(sphere.data.vertices[0].co)

np.random.seed(1)

pixels_polar = []
for i in range(nr_pixels):
	vert_idx = np.random.randint(nr_verts)
	co = sphere.data.vertices[vert_idx].co

	name = "pixel_"+str(i+1).zfill(3)
	bf.create_sphere(name, co, bpy.data.materials.get("ref_pixel").copy(), diameter=0.2, u_segments=16, v_segments=8)

	bpy.data.materials.get("ref_pixel."+str(1).zfill(3)).name = name

	theta = np.arccos(co[2]/radius)

	phi = m.atan2(co[1], co[0])
	# angle = np.arctan(np.abs(co[1]/co[0]))
	# if co[0] > 0 and co[1] > 0:
	# 	phi = angle
	# elif co[0] < 0 and co[1] > 0:
	# 	phi = np.pi - angle
	# elif co[0] < 0 and co[1] < 0:
	# 	phi = np.pi + angle
	# elif co[0] > 0 and co[1] < 0:
	# 	phi = 2*np.pi - angle

	pixels_polar.append({"idx" : str(i+1).zfill(3), "theta" : theta, "phi" : phi})

with open(bpy.path.abspath("//../data/") + 'blender_polar.json', 'w') as fp:
    json.dump(pixels_polar, fp, sort_keys=True, indent=4 * ' ')