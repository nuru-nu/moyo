#!/bin/bash

cd "$(dirname "$0")"


SESSION='rizhom'

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

CM='C-m'
# CM=

MACHINE="${MACHINE:-$(uname -n)}"

FADECANDY='--fadecandy'

case "$MACHINE" in
cervelat*)
  FADECANDY=
  ;;
esac

# create columns
tmux selectp -t 1
tmux splitw -h

# column 1 : recorder, http & players
tmux selectp -t 1
tmux send-keys ". env/bin/activate && cd py" C-m 'python restarter.py $(which python) recorder2.py' $CM
tmux splitw -v -p 66
tmux send-keys ". env/bin/activate && cd py" C-m "cd js" C-M "python -m http.server" $CM
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python) player.py out1' $CM
tmux splitw -h
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python) player.py out2' $CM

# column 2 : fc server, animator & dmx
tmux selectp -t 5
if [ -n -z "$FADECANDY" ]; then
  tmux send-keys ". env/bin/activate && cd fadecandy" C-M "python ../py/restarter.py ./fcserver config.json" $CM
fi
tmux splitw -v -p 66
tmux send-keys ". env/bin/activate && cd py" C-M "python restarter.py $(which python) animator.py $FADECANDY" $CM
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python) dmx.py' $CM
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python) arduino_signals.py' $CM

# # window 2 : git, jupyter
# tmux new-window -t "$SESSION":1 -n dev
# tmux send-keys "echo WOULD RUN JUPYTER HERE..." C-m
# tmux splitw -v -p 80
# tmux send-keys "git status" C-m

tmux attach-session -t "$SESSION"

