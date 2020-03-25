import bpy
import json

bpy.data.objects.keys()

arms = ['arm_1-1', 'arm_1-2', 'arm_2-1', 'arm_2-2', 
		'arm_3-1', 'arm_3-2', 'arm_4-1', 'arm_4-2', 
		'arm_5-1', 'arm_5-2', 'arm_6-1', 'arm_6-2']

sphere = ['strip_0', 'strip_1', 'strip_2', 'strip_3', 
		  'strip_4', 'strip_5', 'strip_6', 'strip_7', 
		  'strip_8', 'strip_9', 'strip_a', 'strip_b', 
		  'strip_c', 'strip_d', 'strip_e', 'strip_f']

kinect_mapping = []
for name in arms + sphere:
	if name not in bpy.data.objects.keys():
		print("Failed! Cant find", name)
		break

	obj = bpy.data.objects[name]

	if len(obj.data.vertices)%60 != 0:
		print("Invalid Nr of pixel vertices in", name)
		break

	for idx, vert in enumerate(obj.data.vertices):
		kinect_mapping.append({"strip_name" : name, "idx" : str(idx).zfill(3), "co" : list(vert.co)}) # "theta" : theta, "phi" : phi
else:
	path = bpy.path.abspath("//data/") + 'kinect_mapping.json'
	print("Saving vertices to", path)
	with open(path, 'w') as fp:
		json.dump(kinect_mapping, fp, sort_keys=True, indent=4 * ' ')
