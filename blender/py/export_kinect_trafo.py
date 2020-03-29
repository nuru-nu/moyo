import bpy
import json

print("Writing transform matrix for currently selected object")

obj = bpy.context.active_object

data = {"scan_name" : obj.data.name, "world_matrix" : [list(row) for row in obj.matrix_world]}
path = bpy.path.abspath("//data/") + 'kinect_trafo.json'
print("Saving trafo to", path)
with open(path, 'w') as fp:
	json.dump(data, fp, sort_keys=True, indent=4 * ' ')
