#!/bin/bash

cd "$(dirname "$0")"

CM=${CM:-C-m}
SERVER=${SERVER:-127.0.0.1}

tmux new-session -d -s nuru_arduino

tmux splitw -v
tmux send-keys './run nuru.integrator'
tmux splitw
tmux send-keys './run nuru.server --server_address 0.0.0.0'
tmux selectp -L
tmux send-keys './run nurulib.arduino --signal_port $(./run nuru.settings integrator_sig_port) --signal_name touch_raw --dev_glob "/dev/ttyACM0*"'

tmux selectp -D
tmux -CC a
