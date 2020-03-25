#!/bin/bash

cd "$(dirname "$0")"


SESSION=nuru

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

CM="${CM:-C-m}"

MACHINE="${MACHINE:-$(uname -n)}"
RESTARTER="./env/bin/python -m smanmi.restarter"
INDEX0="${INDEX0:-1}"

FCSERVER='fcserver'
DMX=yes
OUT2=yes
FADECANDY=--fadecandy

case "$MACHINE" in
cervelat-nuru)
  FCSERVER='./fadecandy/fcserver-osx'
  DMX=
  RESTARTER=
  ;;
cervelat*)
  FCSERVER=
  OUT2=
  DMX=
  FADECANDY=
  RESTARTER=
  ;;
gabriel*)
  FCSERVER=
  OUT2=
  DMX=
  FADECANDY=
  RESTARTER=
  ;;
sanduku)
  FADECANDY=
  DMX=
  RESTARTER=
  OUT2=
  ;;
esac

# create columns
tmux selectp -t $INDEX0
tmux splitw -h
tmux selectp -L

function restarting_cmd() {
  tmux send-keys "$RESTARTER $*" $CM
}

function restarting_py() {
  tmux send-keys "PS1='NURU> '" C-M 'export PYTHONPATH=py' C-M
  restarting_cmd "./env/bin/python -m $*"
}


# column 1 : recorder, cmd/arduino, integrator
restarting_py nuru.recorder

tmux splitw -v -p 66
restarting_py nuru.cmd
tmux splitw -v
tmux selectp -U
tmux splitw -h -p 50
restarting_py nuru.sonar

tmux selectp -D
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
