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
- `py/hotplug_effects.py` : defines how to compute sound effects from audio input & signals
- `py/hotplug_animatinos.py` : defines how to compute visual effects from audio input & signals

programs - start these separately, they communicate on localhost over UDP:

- `py/recorder2.py` : records, plays audio + sends UDP
- `py/monitor.py` : listens UDP, plots + sends commands
- (not used currently) `py/dmx.py` : listens + controls DMX devices - needs
- (needs a running fadecandy server) `py/run_fadecandy_animations.py` : runs the fadecandy animations
- (to simulate neopixels in Blender) `blender/sphere_animation_interface.blend` :
  use Blender to start this (see below for how to set up Blender)
  -> run `blender/py/run_blender_animations.py` INSIDE Blender


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

