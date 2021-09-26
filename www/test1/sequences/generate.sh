#!/bin/bash

# images
# ~2.2M 4896x3264 (1.5:1, 15.98MP)

# videos
# SD,480p         640x480 (1.33:1, 0.31MP)
# HD,720p        1280x720 (1.77:1, 0.92MP)
# Full HD,1080p 1920x1080 (1.77:1, 2.1MP)
# 2K            2048x1152 (1.77:1, 2.4MP)
# UHD,2160p     3840x2160 (1.77:1, 8.3MP)
# DCI 4K,4K     4096x2160 (1.90:1, 8.8MP)
# note that 16:9 == 1.77:1

set -e +x

cd "$(dirname "$0")"

dir="$1"
if [ ! -d "$dir" ]; then
  echo "DIRECTORY \"$dir\" not found!"
  exit -1
fi

if [ "$2" != reuse ]; then
  mkdir -p tmp/
  rm -f tmp/*

  i=0
  n=$(ls -1 $dir/*.JPG | wc -l)
  for path in $(ls $dir/*.JPG); do
    out="tmp/img$(printf '%03d' $i).jpg"
    echo converting $path...
    convert $path -resize 1152x768 -blur 0x$(echo "scale=3; $i/5.0" | bc) $out
    i=$(( i  + 1 ))
  done
fi

out="$(basename "$1")".mp4
ffmpeg -start_number 0 -i tmp/img%03d.jpg -r 25 -b 80M -c:v libx264 -x264opts keyint=1 "$out"
ls -lh "$out"
