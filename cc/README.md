## kinect

### Build it

Build like this:

`mkdir build && cd build && cmake .. && make -j`

### Download Nite

Download Nite from: https://sourceforge.net/projects/roboticslab/files/External/nite/NiTE-Linux-x64-2.2.tar.bz2

tar xvf NiTE-Linux-x64-2.2.tar.bz2
cd NiTE-Linux-x64-2.2
sudo ./install.sh

Alternatively, build without PCL / NiTE (for testing purposes)

`cmake -DUSE_PCL=No -DUSE_NITE=No ..`

### Requirements

- Open CV
- libfreenect2 (and a Kinect One)
- OpenGL (for libfreenect2 pipeline; can probably be commented out)
- PCL
- NiTE (OpenNI)

#### Hacky solution to build Nite

`cd build && git clone https://github.com/totovr/NiTE && cp -r Nite/NiTE-Linux-x64-2.2/Samples/Bin/NiTE2 .`

### Run it

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

### kinect udev rules (arch linux)

Copy the libfreenect udev rules into your system folder to allow access to the kinect without sudo.

sudo cp ~/git/libfreenect2/platform/linux/udev/90-kinect2.rules /etc/udev/rules.d/


### Links for help with linking and dependencies

https://github.com/HukoOo/kinect2_tracker
