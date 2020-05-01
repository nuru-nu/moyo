#!/bin/bash

cd "$(dirname "$0")"


SESSION=nuru

CM="${CM:-C-m}"
LAYOUT="${LAYOUT:-LANDSCAPE}"

MACHINE="${MACHINE:-$(uname -n)}"
RESTARTER="./env/bin/python -m smanmi.restarter"
INDEX0="${INDEX0:-1}"
MIDI_ADDRESS=

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
  MIDI_ADDRESS=127.0.0.1
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


function restarting_cmd() {
  tmux send-keys "$RESTARTER $*" $CM
}

function restarting_py() {
  restarting_cmd "./run $*"
}

tmux start-server
tmux new-session -d -s "$SESSION" -n prod

# start everything
if [ $LAYOUT == LANDSCAPE ]; then
  # create columns
  tmux selectp -t $INDEX0
  tmux splitw -h
  tmux selectp -L

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
  if [ -z "$MIDI_ADDRESS" ]; then
    restarting_py nuru.player out1
  else
    restarting_py nuru.midi --address=$MIDI_ADDRESS
  fi
  if [ ! -z "$OUT2" ]; then
    tmux splitw -h
    restarting_py nuru.player out2
  fi
fi

# start minimum
if [ $LAYOUT == PORTRAIT ]; then
  # row 1
  tmux splitw -v -p 75
  # row 2
  restarting_py nuru.integrator
  tmux splitw -v -p 66
  # row 3
  restarting_py nuru.server
  tmux splitw -v
  # row 4
  restarting_py nuru.midi
  tmux selectp -D
fi

tmux attach-session -t "$SESSION"
