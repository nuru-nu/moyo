# Installation Rizhom 2019

Shared doc : https://docs.google.com/document/d/1DKIEItOe5IRh6JfeMJ1ERkpSYmWZ7JRlewwfzYGTmkQ

## Installation

check out the git repository : `git clone rizhom@figur.li:rizhom.git`

Note that you also need to check out submodules:
- `git submodule init && git submodule update`
- `git pull --recurse-submodules=yes`

### Python packages

virtualenv env
. env/bin/activate
pip install -r requirements.txt
./env/bin/jupyter notebook

OS X
brew install portaudio
pip install --global-option='build_ext' --global-option='-I/usr/local/include' --global-option='-L/usr/local/lib' -r requirements.txt

## Running

analysis:

- `notebooks/audio.ipynb` : record (into `./recordings` repo), analyze, effects
- `notebooks/dmx.ipynb` : install, develop

modules:

- `py/features.py` : extract logmel, ceps
- `py/settings.py` : shared constants
- `py/streaming.py` : continuously calculate & keep state
- `py/util.py` : logging & more
- `py/logic.py` : computes signals in DAG
- `py/hotplug_signals.py` : defines how to compute signals from audio features
- `py/hotplug_effects.py` : defines how to compute sound effects from audio
  input & signals
- `py/hotplug_animatinos.py` : defines how to compute visual effects from
  audio input & signals

programs - start these separately (or use `./launch.sh`), they communicate on
localhost over UDP;

- `py/recorder2.py` : records, plays audio + sends UDP
- `py/animator.py` : runs animations, duplex websocket communication with
   webapp and optionally streams pixels to fadecandy server
- `cd js && python -m http.server` : serves files for the webapp
- `py/player.py` : listens UDP, plays sound on a single sound card (start 
  twice for two soundcards)
- `py/dmx.py` : listens + controls DMX devices - needs
- (to simulate neopixels in Blender)
  `blender/sphere_animation_interface.blend` :
  use Blender to start this (see below for how to set up Blender)
  -> run `blender/py/run_blender_animations.py` INSIDE Blender

deprecated programs:

- `py/monitor.py` : listens UDP, plots + sends commands
- (needs a running fadecandy server) `py/run_fadecandy_animations.py` :
  runs the fadecandy animations

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

### Open ligthning architecture

See instructions in `notebooks/dmx.ipynb` and `py/dmx.py`.

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

jupyter nbextension install --user https://rawgithub.com/minrk/ipython_extensions/master/nbextensions/toc.js
curl -L https://rawgithub.com/minrk/ipython_extensions/master/nbextensions/toc.css > $(jupyter --data-dir)/nbextensions/toc.css
jupyter nbextension enable toc

### 360 images

view with w.g. Google Cardboard:

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

