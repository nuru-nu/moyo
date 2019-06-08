#!/bin/bash

cd "$(dirname "$0")"


SESSION='rizhom'

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

CM='C-m'
# CM=

# create columns
tmux selectp -t 1
tmux splitw -h

# column 1 : recorder, monitor & players
tmux selectp -t 1
tmux send-keys ". env/bin/activate && cd py" C-m 'python restarter.py $(which python3.6) recorder2.py' $CM
tmux splitw -v -p 66
tmux send-keys ". env/bin/activate && cd py" C-M "python monitor.py"
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python3.6) player.py out1' $CM
tmux splitw -h
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python3.6) player.py out2' $CM

# column 2 : fc server, run_animations & dmx
tmux selectp -t 5
tmux send-keys "cd fadecandy" C-M "python ../py/restarter.py ./fcserver config.json" $CM
tmux splitw -v -p 66
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python3.6) run_fadecandy_animations.py' $CM
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python3.6) dmx.py' $CM
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M 'python restarter.py $(which python3.6) arduino_signals.py' $CM

# # window 2 : git, jupyter
# tmux new-window -t "$SESSION":1 -n dev
# tmux send-keys "echo WOULD RUN JUPYTER HERE..." C-m
# tmux splitw -v -p 80
# tmux send-keys "git status" C-m

tmux attach-session -t "$SESSION"

