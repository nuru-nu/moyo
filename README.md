# NURU SHIMONI

Shared doc : https://docs.google.com/document/d/1DKIEItOe5IRh6JfeMJ1ERkpSYmWZ7JRlewwfzYGTmkQ

## Installation

check out the git repository : `git clone smanmi@figur.li:nuru.git`

Note that you also need to check out submodules:
- `git submodule init && git submodule update`
- `git pull --recurse-submodules=yes`

### Speech Emotion Recognition (SER)

https://docs.google.com/document/d/13RMaLnRfHT0_A8e4Z7dG9mOuveXZvXusNEhvAdiNp0U/edit#

https://github.com/audeering/w2v2-how-to

### Kinect OSX install

#### Install libfreenect2

brew install libusb cmake glfw

git clone https://github.com/OpenKinect/libfreenect2.git
cd libfreenect2
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/freenect2
make
make install

export LIBFREENECT2_INSTALL_DIR=$HOME/freenect2
export DYLD_LIBRARY_PATH=$LIBFREENECT2_INSTALL_DIR/lib:$DYLD_LIBRARY_PATH
export CPATH=$LIBFREENECT2_INSTALL_DIR/include:$CPATH

Test

cd $LIBFREENECT2_INSTALL_DIR/bin
./Protonect

#### Install pylibfreenect2

Only necessary if pip install fails!!

mkdir build/include
cp build/libfreenect2 build/include

git clone https://github.com/r9y9/pylibfreenect2.git
cd pylibfreenect2cd

vim setup.py
extra_link_args = ['-stdlib=libc++', '-mmacosx-version-min=10.9']

pip install .

LIBFREENECT2_PATH="$HOME/git/libfreenect2/build/lib"
export DYLD_LIBRARY_PATH="$LIBFREENECT2_PATH:$DYLD_LIBRARY_PATH"

Add EXPORTS to .zsh

### Python packages

```
python3 -m virtualenv env &&
. env/bin/activate &&
pip install -r requirements.txt
```

note that on OS X you have to install portaudio & specify some extra parameters:

Install with brew
brew install portaudio
find / -name portaudio.h 2>/dev/null # Find the port audio, usually in ~/homebrew/
CFLAGS="-I/path_to_ort_audio/include -L/path_to_ort_audio/lib" python -m pip install pyaudio


```
brew install portaudio &&
pip install --global-option='build_ext' --global-option='-I/usr/local/include' --global-option='-L/usr/local/lib' -r requirements.txt
```

## Running

The sript `./launch.sh` starts a couple of programs that constitute the
different components of the installation. See the package pydoc for additional
information. Then go to <http://localhost:8080>.

The default setup requires the MIDI bridge to be run separately on `mbp.local`
via the `./launch_midi.sh` script.

Alternatively start `./launch_sim.sh` for development purposes.

### Communication between programs

referring to ports in `settings.py`:

- `recorder2.py` -> `animator.py:monitor_port` : signals
- `animator.py` -> `recorder2.py` : signalin
- * -> `settings.status_address`:`settings.status_port` : status

signals protocol: JSON encoded signals, all scalars except:

- logmel
- mfccs
- state

signalin protocol: JSON encoded instructions (ES6 notation):

- signalin
- `{logmel_src}` with possible values `input`, `output0`, `output1`
- `{newstate}` with possible values `frozen` or any state name
- `{overrides: {signal1: value1, ...}}` : applied in `logic.SignalRunner`

status protocol:

- JSON encoded {name, statust, ip}
- defaults to send to `figur.li`

### Remote maintenance

- connect to remote server, forwarding local SSH port for back-login
- forward UDP ports using `socat` (signalin 6101 remote->local and status 6107 local->signalin):
- see also convenient `./launch_maintenance.sh`

```
locally:

# socat -T15 udp4-recvfrom:6107,reuseaddr,fork tcp:localhost:6107
socat tcp4-listen:6101,reuseaddr,fork udp:localhost:6101
ssh -i ~/.ssh/rizhom -R6122:localhost:22 -R6101:localhost:6101 -L6107:localhost:6107 rizhom@figur.li

remotely:

socat -T15 udp4-recvfrom:6101,reuseaddr,fork tcp:localhost:6101
# socat tcp4-listen:6107,reuseaddr,fork udp:localhost:6107
```

then there are two standalone programs to be run on the remote server:

- `py/server.py` : web interface for displaying status & sending commands
- `py/signalin.py` : send commands via command line

## Development

For an overview, see [Slides]

[Slides]: https://docs.google.com/presentation/d/1kWKOjcJiLdcVQkaqHcMZZdBt3DM2olypaQvjHZF1c8I

### vscode settings

- Python linter: flake8

### Open ligthning architecture

See instructions in `notebooks/dmx.ipynb` and `py/nuru/dmx.py`.

### Blender

We use Blender to simulate the Neopixel

tested with Blender 2.79b
cd /Applications/Blender/blender.app/Contents/Resources/2.79/python/bin
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
./python3.5m get-pip.py
C_INCLUDE_PATH=/usr/local/Cellar/python//3.6.4_2/Frameworks/Python.framework/Versions/3.6/include/python3.6m ./pip3 install scipy pyaudio
ln -s /Applications/Blender/blender.app/Contents/Resources/2.79/python/lib/python3.5/site-packages /Applications/Blender/blenderplayer.app/Contents/Resources/2.79/python/lib/python3.5/site-packages
(also renamed old numpy installation)

### Git

git config status.submodulesummary 1

### VIM config

https://github.com/Vimjas/vim-python-pep8-indent.git
https://github.com/vim-syntastic/syntastic/
let g:syntastic_python_flake8_config_file='.flake8'
set cc=80

### Jupyter


Jupyter is part of the requirements installed above under "Python packages". It
can be run via `jupyter lab`. The notebooks are stored in the `notebooks/`.

Additional useful extensions:

```
nvm use current
jupyter labextension install @jupyterlab/toc
```

### 360 images

View with w.g. Google Cardboard:

- https://play.google.com/store/apps/details?id=com.xojot.vrplayer

### train new networks

1. (monitor.py create more recordings
2. (recordings.ipynb) extract recordings to ABase format
3. (recordings.ipynb) update transformed features
4. (tf.ipynb) create new `classes` configuration if needed
5. (tf.ipynb) maybe add more hyperparameters
6. (tf.ipynb) run experiments
7. (tf.ipynb) store new model
8. (hotplug_signals.ipynb) load & use new model
