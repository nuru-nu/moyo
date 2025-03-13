#!/bin/bash

cd "$(dirname "$0")"

CM=${CM:-C-m}
SERVER=${SERVER:-0.0.0.0}

tmux start-server
tmux new-session -d -s nuru

# cmd

## column 1
tmux splitw -h
tmux selectp -L
# row 1
tmux send-keys '(cd cc/build; DISPLAY=:1 ./kinect --no-gui)' $CM
# row 2
tmux splitw -p 75
tmux send-keys './run nuru.recorder' $CM
# row 3
tmux splitw -p 66
tmux send-keys './run nurulib.arduino --signal_port $(./run nuru.settings integrator_sig_port) --dev_glob /dev/ttyUSB* /dev/ttyACM*' $CM
# row 4
tmux splitw
tmux send-keys './run nuru.integrator --midi_address=$(``./getip.sh`` mbp.local)' $CM

## column 2
tmux selectp -R
# row 1
tmux send-keys 'sleep 3' 'C-m' './run nuru.server --port=0 --fadecandy' $CM
# row 2
tmux splitw -p 75
tmux send-keys '(cd fadecandy; ./fcserver config.json)' $CM
# row 3
tmux splitw -p 66
tmux send-keys "./run nuru.server --server_address=${SERVER} --fps=0 --instance=2" $CM
# row 4
tmux splitw
tmux send-keys "./run nuru.server --server_address=${SERVER} --fps=0 --instance=3 --index=index2.html --port=8081" $CM
# tmux send-keys './run nuru.dmx' $CM
# row 4
# tmux splitw -p 66
# tmux send-keys './run nuru.midi' $CM

# player out1; player out2

tmux attach-session
