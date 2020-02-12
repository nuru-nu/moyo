## kinect

Build like this:

`mkdir build && cd build && cmake .. && make`

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

