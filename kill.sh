#!/bin/bash

if [ "$(uname -s)" == 'Darwin' ]; then
  # -HUP seems not to work as it should ?!
  ps | grep './env/bin/python -m' | awk '{print $1}' | xargs kill
  killall kinect
fi
tmux kill-session -t nuru
