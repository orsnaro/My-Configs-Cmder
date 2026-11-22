#!/usr/bin/env bash
set -euo pipefail

state_dir="${XDG_RUNTIME_DIR:-$HOME/.cache}/ml4w"
mkdir -p "$state_dir"
exec 9>"$state_dir/gamemode-dock.lock"
flock 9

# Reuse the existing game-mode state and effects; serialize repeated presses.
bash "$HOME/.config/hypr/scripts/gamemode.sh" 9>&-

if [[ -f "$HOME/.config/ml4w/settings/gamemode-enabled" ]]; then
    "$HOME/.local/bin/ml4w-dock" stop
else
    # The dock lives beyond this toggle and must not keep its lock open.
    "$HOME/.local/bin/ml4w-dock" start 9>&- >>"$state_dir/gamemode-dock.log" 2>&1 &
fi
