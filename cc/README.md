## kinect

Build like this:

`mkdir build && cd build && cmake .. && make -j`

Note: The library can also be built without PCL / NiTE support:

`cmake -DUSE_PCL=No -DUSE_NITE=No ..`

Then the executable `kinect` shows images from Kinect and sends signals to
signalin port.

Some keyboard shortcuts (when then window has focus):

- `<TAB>` : switch display framerate
- `<SPACE>` : initialize background from current frame
- `q` : quit (same as pressing `<CTRL-C>` in the terminal)


### requirements

- Open CV
- libfreenect2 (and a Kinect One)
- OpenGL (for libfreenect2 pipeline; can probably be commented out)

Optional;

- PCL
- NiTE (OpenNI)
