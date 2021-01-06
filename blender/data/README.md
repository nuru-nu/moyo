# Blender data

## Transformation matrices

- kinect_trafo.json : the one that's exported by the Blender script
  `export_kinect_trafo.py` and that is actually used by `kinect.cc`
- kinect_trafo_0.json : original attic trafo - works pretty well for the "1"
  markings on the attic as well.
- kinect_trafo_1.json : attic trafo marked "1" on the floor - for some
  mysterious reason this one is NOT WORKING (at least the Y direction is
  switched).
- kinect_trafo_2.json : attic trafo marked "2" on the floor 
