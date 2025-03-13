#!/bin/bash
cd "$(dirname "$0")"
CM=${CM:-C-m}
SERVER=${SERVER:-0.0.0.0}

# Kill any existing session
tmux kill-session -t nuru 2>/dev/null || true

# Create new session
tmux new-session -d -s nuru

# Create layout manually, one step at a time
# First create two columns
tmux split-window -h

# In the LEFT column (which is now the active pane)
# Create first split
tmux split-window -v
# Create second split in the top pane
tmux select-pane -U
tmux split-window -v
# Create third split in the top pane
tmux select-pane -U
tmux split-window -v

# Go to the RIGHT column
tmux select-pane -R
# Create first split
tmux split-window -v
# Create second split in the top pane
tmux select-pane -U
tmux split-window -v
# Create third split in the top pane
tmux select-pane -U
tmux split-window -v

# Now send commands to each pane using the %pane_id notation
# First, get all pane IDs
PANES=($(tmux list-panes -F "#{pane_id}"))

# Left column (panes 0-3)
tmux send-keys -t ${PANES[0]} './run nuru.video_stream_gpt --display_stream --img_gpt_stream --run_yolo' $CM
tmux send-keys -t ${PANES[1]} '(cd fadecandy; ./fcserver-osx config.json)' $CM
tmux send-keys -t ${PANES[2]} './run nuru.midi' $CM
tmux send-keys -t ${PANES[3]} './run nuru.integrator' $CM

# Right column (panes 4-7)
tmux send-keys -t ${PANES[4]} "ssh nurulib@nuru.nu -R9898:localhost:8081" $CM
tmux send-keys -t ${PANES[5]} "./run nuru.server --server_address=${SERVER} --fadecandy" $CM
tmux send-keys -t ${PANES[6]} "./run nuru.server --fps=0 --instance=2 --index=index3.html --port=8081" $CM
tmux send-keys -t ${PANES[7]} "./run nuru.server --fps=0 --instance=3 --index=index4.html --port=8082" $CM

# Attach to session
tmux attach-session -t nuru