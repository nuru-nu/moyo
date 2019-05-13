# Installation Rizhom 2019

Shared doc : https://docs.google.com/document/d/1DKIEItOe5IRh6JfeMJ1ERkpSYmWZ7JRlewwfzYGTmkQ

## Installation

### Python packages

virtualenv env
. env/bin/activate
pip install -r requirements.txt
./env/bin/ipython kernel install --user --name=rizhom
./env/bin/jupyter notebook

OS X
brew install portaudio
pip install --global-option='build_ext' --global-option='-I/usr/local/include' --global-option='-L/usr/local/lib' -r requirements.txt

### 360 images

view with w.g. Google Cardboard:

- https://play.google.com/store/apps/details?id=com.xojot.vrplayer

## Use

Note that you might also want to check out submodules:
`git submodule init && git submodule update`

analysis:

- `notebooks/audio.ipynb` : record (into `./recordings` repo), analyze, effects
- `notebooks/dmx.ipynb` : install, develop

modules:

- `py/features.py` : extract logmel, ceps
- `py/settings.py` : shared constants
- `py/streaming.py` : continuously calculate & keep state
- `py/util.py` : logging & more

programs:

- `py/dmx.py` : listens + controls DMX devices
- `py/monitor.py` : listens UDP, plots + sends commands
- `py/recorder2.py` : records, plays audio + sends UDP


### Open ligthning architecture

See instructions in `notebooks/dmx.ipynb` and `py/dmx.py`.

## Development

### Blender

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

