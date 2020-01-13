#!/bin/bash

cd "$(dirname "$0")"


SESSION=nuru

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

CM='C-m'
# CM=

MACHINE="${MACHINE:-$(uname -n)}"

FCSERVER='fcserver'
ARDUINO=yes
DMX=yes
OUT2=yes

case "$MACHINE" in
cervelat*)
  ARDUINO=
  DMX=
  FCSERVER='fcserver-osx'
  OUT2=
  ;;
esac

# create columns
tmux selectp -t 1
tmux splitw -h

function restarting_cmd() {
  tmux send-keys '. env/bin/activate' C-M "PYTHONPATH=py python -m smanmi.restarter $*" $CM
}

function restarting_py() {
  restarting_cmd "\$(which python) -m $*"
}

# column 1 : recorder, http & players
tmux selectp -t 1
restarting_py nuru.recorder2
tmux splitw -v -p 66
tmux send-keys '. ./env/bin/activate' C-M 'cd js && python -m http.server' $CM
tmux splitw -v
restarting_py nuru.player out1
tmux splitw -h
if [ ! -z "$OUT2" ]; then
  restarting_py nuru.player out2
fi

# column 2 : fc server, animator & dmx
tmux selectp -t 5
if [ ! -z "$FADECANDY" ]; then
  restarting_cmd "$FCSERVER" fadecandy/config.json
  tmux splitw -v -p 66
fi
restarting_py nuru.animator
if [ ! -z "$DMX" ]; then
  tmux splitw -v
  restarting_py nuru.dmx
fi
if [ ! -z "$ARDUINO" ]; then
  tmux splitw -v
  restarting_py nuru.sonar
fi

# # window 2 : git, jupyter
# tmux new-window -t "$SESSION":1 -n dev
# tmux send-keys "echo WOULD RUN JUPYTER HERE..." C-m
# tmux splitw -v -p 80
# tmux send-keys "git status" C-m

tmux attach-session -t "$SESSION"
