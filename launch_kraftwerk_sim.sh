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
tmux send-keys './run nuru.video_stream_gpt --display_stream --gpt_img_div 4 --img_gpt_stream' $CM
# row 2
tmux splitw -p 60
tmux send-keys '(cd fadecandy; ./fcserver-osx config.json)' $CM
# row 4
tmux splitw
tmux send-keys './run nuru.midi' $CM

## column 2
tmux selectp -R
# row 1
tmux send-keys "./run nuru.integrator" $CM
# row 2
tmux splitw -p 60
tmux send-keys "./run nuru.server --server_address=${SERVER} --fadecandy" $CM
# row 3
tmux splitw
tmux send-keys "./run nuru.server --fps=0 --instance=3 --index=index3.html --port=8081" $CM

tmux selectp -D
tmux attach-session
