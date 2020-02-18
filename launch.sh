#!/bin/bash

cd "$(dirname "$0")"


SESSION=nuru

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

CM="${CM:-C-m}"

MACHINE="${MACHINE:-$(uname -n)}"
RESTARTER="python -m smanmi.restarter"
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
  RESTARTER=
  ;;
gabriel*)
  FCSERVER=
  OUT2=
  ARDUINO=
  DMX=
  FADECANDY=
  RESTARTER=
  ;;
esac

# create columns
tmux selectp -t $INDEX0
tmux splitw -h

function restarting_cmd() {
  tmux send-keys '. env/bin/activate' C-M "PYTHONPATH=py $RESTARTER $*" $CM
}

function restarting_py() {
  restarting_cmd "\$(which python) -m $*"
}


# column 1 : recorder, arduino, integrator
tmux selectp -t $INDEX0
restarting_py nuru.recorder

if [ ! -z "$ARDUINO" ]; then
  tmux splitw -v -p 66
  restarting_py nuru.sonar
fi

tmux splitw -v
restarting_py nuru.integrator


# column 2 : server, fc server, dmx, players
tmux selectp -R
restarting_py nuru.server "$FADECANDY"

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


tmux attach-session -t "$SESSION"
