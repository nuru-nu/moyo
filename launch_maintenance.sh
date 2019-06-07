#!/bin/bash

cd "$(dirname "$0")"


SESSION='maintenance'

tmux start-server

tmux new-session -d -s "$SESSION" -n prod

# create columns
tmux selectp -t 1
tmux splitw -h

# column 1 : ssh
tmux selectp -t 1
# expected processes on server:
# socat -T15 udp4-recvfrom:6101,reuseaddr,fork tcp:localhost:6101
# socat tcp4-listen:6107,reuseaddr,fork udp:localhost:6107
tmux send-keys "while true; do ssh -i ~/.ssh/rizhom -R6122:localhost:22 -R6101:localhost:6101 -L6107:localhost:6107 rizhom@figur.li; done" C-m "tmux attach" C-m

# column 2 : fc server & run_animations
tmux selectp -t 2
tmux splitw -v
tmux selectp -t 2
tmux send-keys "socat tcp4-listen:6101,reuseaddr,fork udp:localhost:6101"
tmux splitw -v
tmux selectp -t 3
# tmux send-keys "socat -T15 udp4-recvfrom:6107,reuseaddr,fork tcp:localhost:6107"
tmux send-keys "scp py/server.py rizhom@figur.li:"

tmux attach-session -t "$SESSION"