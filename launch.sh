#!/bin/bash

cd "$(dirname "$0")"


SESSION=nuru

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

CM='C-m'
# CM=

MACHINE="${MACHINE:-$(uname -n)}"
INDEX0="${INDEX0:-1}"

FCSERVER='fcserver'
ARDUINO=yes
DMX=yes
OUT2=yes
FADECANDY=--fadecandy

case "$MACHINE" in
cervelat-nuru)
  FCSERVER='fcserver-osx'
  DMX=
  ;;
cervelat*)
  FCSERVER=
  OUT2=
  ARDUINO=
  DMX=
  FADECANDY=
  ;;
esac

# create columns
tmux selectp -t $INDEX0
tmux splitw -h

function restarting_cmd() {
  tmux send-keys '. env/bin/activate' C-M "PYTHONPATH=py python -m smanmi.restarter $*" $CM
}

function restarting_py() {
  restarting_cmd "\$(which python) -m $*"
}


# column 1 : recorder, arduino, integrator, http
tmux selectp -t $INDEX0
restarting_py nuru.recorder

if [ ! -z "$ARDUINO" ]; then
  tmux splitw -v -p 75
  restarting_py nuru.sonar
fi

tmux splitw -v -p 66
restarting_py nuru.integrator

tmux splitw -v
tmux send-keys '. ./env/bin/activate' C-M 'cd js && python -m http.server' $CM


# column 2 : animator, fc server, dmx, players
tmux selectp -R
restarting_py nuru.animator "$FADECANDY"

if [ ! -z "$FCSERVER" ]; then
  restarting_cmd "$FCSERVER" fadecandy/config.json
  tmux splitw -v -p 75
fi

if [ ! -z "$DMX" ]; then
  tmux splitw -v -p 66
  restarting_py nuru.dmx
fi

tmux splitw -v
restarting_py nuru.player out1
if [ ! -z "$OUT2" ]; then
  tmux splitw -h
  restarting_py nuru.player out2
fi


# # window 2 : git, jupyter
# tmux new-window -t "$SESSION":1 -n dev
# tmux send-keys "echo WOULD RUN JUPYTER HERE..." C-m
# tmux splitw -v -p 80
# tmux send-keys "git status" C-m

tmux attach-session -t "$SESSION"
