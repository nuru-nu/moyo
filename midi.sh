#!/bin/bash

cd "$(dirname "$0")"
. ./utils.sh

CM=${CM:-C-m}

tmux start-server
tmux new-session -d -s midi

# row 1
# row 2
tmux splitw -v -p 75
tmux send-keys "./run nuru.midi --integrator_address=$(getip sanduku.local)" $CM

tmux selectp -D
tmux attach-session
