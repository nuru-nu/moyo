#!/bin/bash

cd "$(dirname "$0")"


SESSION='rizhom'

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

# create columns
tmux selectp -t 1
tmux splitw -h

# column 1 : recorder, monitor & player
tmux selectp -t 1
tmux send-keys ". env/bin/activate && cd py" C-m "python recorder2.py" C-m
tmux splitw -v -p 66
tmux send-keys ". env/bin/activate && cd py" C-M "python monitor.py" C-m
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M "python player.py" C-m

# column 2 : fc server & run_animations
tmux selectp -t 4
tmux send-keys "cd fadecandy" C-M "./fadecandy_server config.json" C-m
tmux splitw -v
tmux send-keys ". env/bin/activate && cd py" C-M "python run_fadecandy_animations.py" C-m

# # window 2 : git, jupyter
# tmux new-window -t "$SESSION":1 -n dev
# tmux send-keys "echo WOULD RUN JUPYTER HERE..." C-m
# tmux splitw -v -p 80
# tmux send-keys "git status" C-m

tmux attach-session -t "$SESSION"

