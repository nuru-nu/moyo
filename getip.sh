#!/bin/bash

if [ $(uname) = Darwin ]; then
    ping -c1 $1 | head -1 | sed -e's/.*(\(.*\)).*/\1/'
elif [ $(uname -n) = sanduku ]; then
    avahi-resolve-host-name -4 $1 | awk '{print $2}'
else
    echo CANNOT GET IP
fi
