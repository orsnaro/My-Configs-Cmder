#!/bin/sh
# refresh-avatar.sh [IMAGE]: puts your picture (IMAGE, or ~/.face) where the login screen reads it. No sudo: the folder is yours (install.sh made it). Vitreus's Settings does this when you change your picture.
shared=/usr/local/share/vitreus-greeter
src=${1:-$HOME/.face}
[ -d "$shared" ] || { echo "the login screen is not installed (no $shared)" >&2; exit 1; }
[ -f "$src" ] || { echo "no picture at $src" >&2; exit 1; }
magick "$src[0]" -auto-orient -resize 512x512^ -gravity center -extent 512x512 "$shared/avatar.png"
chmod a+r "$shared/avatar.png"
echo "the login screen shows $src now"
