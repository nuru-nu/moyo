#!/bin/bash

cd "$(dirname "$0")"

CM=${CM:-C-m}
SERVER=${SERVER:-127.0.0.1}

tmux start-server
tmux new-session -d -s nuru

# row 1
tmux send-keys "./run nuru.integrator" $CM
# row 2
tmux splitw -v -p 75
tmux send-keys "./run nuru.server --server_address=${SERVER}" $CM
# row 3
tmux splitw -v -p 66
tmux send-keys "./run nuru.midi" $CM

tmux selectp -D
tmux attach-session
