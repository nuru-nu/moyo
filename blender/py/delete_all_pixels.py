import bpy

nr_pixels = 5*60

for i in range(0,nr_pixels):
	obj = bpy.data.objects['pixel_'+str(i+1).zfill(3)]
	obj.select = True

	bpy.ops.object.delete()

for material in bpy.data.materials:
	if material.name[:5] == 'pixel':
		material.user_clear()
		bpy.data.materials.remove(material)