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

- `notebooks/audio.ipynb` : record (into `./recordings` repo), analyze, effects
- `notebooks/dmx.ipynb` : install, develop
- `py/features.py` : extract logmel, ceps
- `py/monitor.py` : real time analyze & interact
- `py/recorder2.py` : record + play audio
- `py/settings.py` : shared constants
- `py/streaming.py` : continuously calculate & keep state
- `py/util.py` : logging & more


### Open ligthning architecture

See instructions in `notebooks/dmx.ipynb`.

## Development

### Git

git config status.submodulesummary 1

### VIM config

https://github.com/Vimjas/vim-python-pep8-indent.git
https://github.com/vim-syntastic/syntastic/
let g:syntastic_python_flake8_config_file='.flake8'
set cc=80

