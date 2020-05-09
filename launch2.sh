#!/bin/bash

# WIP more minimal launch.sh

cd "$(dirname "$0")"

tmux start-server
tmux new-session

# row 1
tmux splitw -v -p 75
# row 2
tmux send-keys "./run nuru.integrator" C-m
tmux splitw -v -p 66
# row 3
tmux send-keys "./run nuru.server" C-m
tmux splitw -v
# row 4
tmux send-keys "./run nuru.midi" C-m
tmux selectp -D
