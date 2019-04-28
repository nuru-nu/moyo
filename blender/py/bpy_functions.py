import bpy
import bmesh
import numpy as np

def create_sphere(name, location, material, diameter=1, u_segments=32, v_segments=16):
	# Create an empty mesh and the object.
	scn = bpy.context.scene
	mesh = bpy.data.meshes.new(name)
	basic_sphere = bpy.data.objects.new(name, mesh)

	# Add the object into the scene.
	bpy.context.scene.objects.link(basic_sphere)
	bpy.context.scene.objects.active = basic_sphere
	basic_sphere.select = True

	# Construct the bmesh sphere and assign it to the blender mesh.
	bm = bmesh.new()
	bmesh.ops.create_uvsphere(bm, u_segments=u_segments, v_segments=v_segments, diameter=diameter)
	bm.to_mesh(mesh)
	bm.free()

	basic_sphere.location = location
	basic_sphere.data.materials.append(material)

def dist_point_to_line(a, b, p): 	# Line between a and b. Point p
    return np.linalg.norm(np.cross(b-a, a-p))/np.linalg.norm(b-a)	

def find_closest_vert_idx(obj, phi, theta):
	p0 = np.array([0,0,0])
	p1 = np.array([100*np.sin(theta)*np.cos(phi),100*np.sin(theta)*np.sin(phi),100*np.cos(theta)])
	closest_point = [0, 10000]
	for vert in obj.data.vertices:
		dist = dist_point_to_line(p0, p1, vert.co)
		if dist < closest_point[1]:
			closest_point = [vert.index, dist]
	return closest_point[0]



# obj = bpy.context.active_object
# mat = obj.active_material
# mesh = obj.data

# dup = bpy.data.objects.new(obj.name, mesh.copy())
# dup.active_material = bpy.data.materials.get("pixel").copy()
# scn.objects.link(dup)