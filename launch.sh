#!/bin/bash

cd "$(dirname "$0")"
. ./utils.sh

CM=${CM:-C-m}
SERVER=${SERVER:-0.0.0.0}

tmux start-server
tmux new-session -d -s nuru

# cmd

## column 1
tmux splitw -h
tmux selectp -L
# row 1
tmux send-keys '(cd cc/build; ./kinect)' $CM
# row 2
tmux splitw -p 75
tmux send-keys './run nuru.recorder' $CM
# row 3
tmux splitw -p 66
tmux send-keys './run nuru.sonar' $CM
# row 4
tmux splitw
tmux send-keys "./run nuru.integrator --midi_address=$(getip mbp.local)" $CM

## column 2
tmux selectp -R
# row 1
tmux send-keys "./run nuru.server --server_address=${SERVER} --fadecandy" $CM
# row 2
tmux splitw -p 75
tmux send-keys '(cd fadecandy; sudo ./fcserver config.json)' $CM
# row 3
tmux splitw -p 66
tmux send-keys './run nuru.dmx' $CM
# row 4
# tmux splitw -p 66
# tmux send-keys './run nuru.midi' $CM

# player out1; player out2

tmux attach-session
