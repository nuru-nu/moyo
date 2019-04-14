import bpy
import bmesh

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


# obj = bpy.context.active_object
# mat = obj.active_material
# mesh = obj.data

# dup = bpy.data.objects.new(obj.name, mesh.copy())
# dup.active_material = bpy.data.materials.get("pixel").copy()
# scn.objects.link(dup)