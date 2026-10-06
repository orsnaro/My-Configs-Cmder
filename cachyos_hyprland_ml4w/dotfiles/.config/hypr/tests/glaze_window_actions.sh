#!/usr/bin/env bash
set -euo pipefail
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
cat > "$test_dir/hyprctl" <<'FAKE'
#!/usr/bin/env bash
case "$1 $2" in
    'activewindow -j') printf '%s\n' "$ACTIVE_JSON" ;;
    'monitors -j') printf '%s\n' "$MONITORS_JSON" ;;
    'dispatch '*) printf '%s\n' "$2" >> "$COMMAND_LOG" ;;
    *) echo "Unexpected hyprctl: $*" >&2; exit 1 ;;
esac
FAKE
chmod +x "$test_dir/hyprctl"
export PATH="$test_dir:$PATH" COMMAND_LOG="$test_dir/dispatches"
export MONITORS_JSON='[{"id":0,"name":"DP-2","x":2404,"y":381,"width":2560,"height":1440},{"id":1,"name":"HDMI-A-2","x":1038,"y":768,"width":1366,"height":768},{"id":2,"name":"DP-1","x":4964,"y":768,"width":1440,"height":900}]'
export ACTIVE_JSON='{"address":"0xabc","class":"kitty","monitor":0,"floating":false,"workspace":{"id":1,"name":"1"}}'

move="$HOME/.local/bin/glaze-move-window"
resize="$HOME/.local/bin/glaze-resize-window"

"$move" left
grep -Fx 'hl.dsp.window.move({ direction = "l" })' "$COMMAND_LOG"
: > "$COMMAND_LOG"
export ACTIVE_JSON='{"address":"0xabc","class":"kitty","monitor":0,"floating":true,"workspace":{"id":1,"name":"1"}}'
"$move" right
grep -Fx 'hl.dsp.window.move({ x = 384, y = 0, relative = true })' "$COMMAND_LOG"
: > "$COMMAND_LOG"
"$move" monitor right
grep -Fx 'hl.dsp.window.move({ monitor = "DP-1", follow = true })' "$COMMAND_LOG"
: > "$COMMAND_LOG"
"$move" monitor left
grep -Fx 'hl.dsp.window.move({ monitor = "HDMI-A-2", follow = true })' "$COMMAND_LOG"
: > "$COMMAND_LOG"
"$resize" width -2
grep -Fx 'hl.dsp.window.resize({ x = -51, y = 0, relative = true })' "$COMMAND_LOG"
: > "$COMMAND_LOG"
export ACTIVE_JSON='{"address":"0xabc","class":"kitty","monitor":2,"floating":false,"workspace":{"id":7,"name":"7"}}'
"$move" monitor up
grep -Fx 'hl.dsp.window.move({ direction = "u" })' "$COMMAND_LOG"
: > "$COMMAND_LOG"
export ACTIVE_JSON='{"address":"0xabc","class":"kitty","monitor":2,"floating":true,"workspace":{"id":7,"name":"7"}}'
"$move" monitor up
grep -Fx 'hl.dsp.window.move({ x = 0, y = -135, relative = true })' "$COMMAND_LOG"

echo 'PASS: tiled/floating moves, monitor transfers, and percentage resize'
