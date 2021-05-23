#!/bin/bash

cd "$(dirname "$0")"

CM=${CM:-C-m}
SERVER=${SERVER:-127.0.0.1}

tmux start-server
tmux new-session -d -s nuru

# row 1
# row 2
tmux splitw -v
tmux send-keys './run nuru.midi --integrator_address=$(./getip.sh sanduku.local)' $CM

tmux selectp -D
tmux attach-session
