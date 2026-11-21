#!/usr/bin/env bash
# Keep the 1080p master and limit the bandwidth needed on a tablet.
set -euo pipefail
if [[ $# != 2 ]]; then
    printf 'Usage: %s input.mp4 output.mp4\n' "$0" >&2
    exit 2
fi
ffmpeg -hide_banner -loglevel error -y -i "$1" \
    -map 0:v:0 -map 0:a:0 -c:v libx264 -preset medium -tune animation \
    -crf 19 -maxrate 960k -bufsize 1500k -g 50 -threads 1 -pix_fmt yuv420p \
    -c:a aac -b:a 96k -movflags +faststart "$2"
