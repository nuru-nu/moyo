#!/bin/bash

if [ "$(uname -s)" == 'Darwin' ]; then
  echo '### THIS WILL PROBABLY NOT WORK FOR YOU ###'
fi
tmux kill-session -t nuru
