import bpy
import numpy as np
import os.path, sys
import json
import math as m
import importlib
import bpy_functions as bf
importlib.reload(bf)


lib_path = bpy.path.abspath("//../py/")
assert os.path.exists(lib_path), 'Make sure "." path is where notebooks are!'
if not lib_path in sys.path:
    sys.path.insert(0, lib_path)

import audio, features, settings, util

riz_hole = bpy.data.objects['rizhom_hole']
nr_pixels = 10*60


np.random.seed(1)

polars = np.array(util.phi_theta_samples(nr_pixels)).T
# print(nr_pixels, len(polars))
pixels_polar = []
for i, polar in enumerate(polars):
	idx = bf.find_closest_vert_idx(riz_hole, polar[0], polar[1])
	co = np.array(riz_hole.data.vertices[idx].co)

	name = "pixel_"+str(i+1).zfill(3)
	bf.create_sphere(name, co, bpy.data.materials.get("ref_pixel").copy(), diameter=0.3, u_segments=16, v_segments=8)
	bpy.data.materials.get("ref_pixel."+str(1).zfill(3)).name = name

	theta = np.arccos(co[2]/np.sqrt(co[0]**2 + co[1]**2 + co[2]**2))
	phi = m.atan2(co[1], co[0])

	print(i, "co:", co, "polar rand val:", polar, "polar idx val:", phi, theta)

	pixels_polar.append({"idx" : str(i+1).zfill(3), "theta" : theta, "phi" : phi})

with open(bpy.path.abspath("//../data/") + 'blender_polar.json', 'w') as fp:
    json.dump(pixels_polar, fp, sort_keys=True, indent=4 * ' ')



# nr_verts = len(riz_hole.data.vertices)
# radius = np.linalg.norm(riz_hole.data.vertices[0].co)
# pixels_polar = []
# for i in range(nr_pixels):
# 	vert_idx = np.random.randint(nr_verts)
# 	co = riz_hole.data.vertices[vert_idx].co

# 	name = "pixel_"+str(i+1).zfill(3)
# 	bf.create_sphere(name, co, bpy.data.materials.get("ref_pixel").copy(), diameter=0.5, u_segments=16, v_segments=8)

# 	bpy.data.materials.get("ref_pixel."+str(1).zfill(3)).name = name

# 	theta = np.arccos(co[2]/np.sqrt(co[0]**2 + co[1]**2) + co[2]**2)

# 	phi = np.arctan2(co[1], co[0])

# 	# angle = np.arctan(np.abs(co[1]/co[0]))
# 	# if co[0] > 0 and co[1] > 0:
# 	# 	phi = angle
# 	# elif co[0] < 0 and co[1] > 0:
# 	# 	phi = np.pi - angle
# 	# elif co[0] < 0 and co[1] < 0:
# 	# 	phi = np.pi + angle
# 	# elif co[0] > 0 and co[1] < 0:
# 	# 	phi = 2*np.pi - angle

# 	pixels_polar.append({"idx" : str(i+1).zfill(3), "theta" : theta, "phi" : phi})

# with open(bpy.path.abspath("//../data/") + 'blender_polar.json', 'w') as fp:
#     json.dump(pixels_polar, fp, sort_keys=True, indent=4 * ' ')