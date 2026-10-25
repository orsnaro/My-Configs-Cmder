#!/usr/bin/env bash
set -euo pipefail
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
cat > "$test_dir/hyprctl" <<'FAKE'
#!/usr/bin/env bash
case "$1 $2" in
    'cursorpos -j') printf '%s\n' '{"x":5100,"y":1000}' ;;
    'monitors -j') printf '%s\n' "$MONITORS_JSON" ;;
    'clients -j') printf '%s\n' "$CLIENTS_JSON" ;;
    'dispatch '*) printf '%s\n' "$2" >> "$COMMAND_LOG" ;;
    *) echo "Unexpected hyprctl: $*" >&2; exit 1 ;;
esac
FAKE
cat > "$test_dir/kitty" <<'FAKE'
#!/usr/bin/env bash
printf 'kitty %s\n' "$*" >> "$COMMAND_LOG"
sleep 1
FAKE
chmod +x "$test_dir/hyprctl" "$test_dir/kitty"
export PATH="$test_dir:$PATH" COMMAND_LOG="$test_dir/commands" XDG_RUNTIME_DIR="$test_dir"
export MONITORS_JSON='[{"id":0,"name":"DP-2","x":2404,"y":381,"width":2560,"height":1440,"focused":false,"specialWorkspace":{"name":""}},{"id":2,"name":"DP-1","x":4964,"y":768,"width":1440,"height":900,"focused":true,"specialWorkspace":{"name":""}}]'
export CLIENTS_JSON='[]'

"$HOME/.local/bin/glaze-quake"
sleep 0.1
grep -Fx 'hl.dsp.focus({ monitor = "DP-1" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.workspace.toggle_special("quake")' "$COMMAND_LOG"
grep -F 'kitty --class quake-kitty' "$COMMAND_LOG"
test "$(grep -c '^kitty ' "$COMMAND_LOG")" -eq 1

: > "$COMMAND_LOG"
export CLIENTS_JSON='[{"address":"0xabc","class":"quake-kitty","workspace":{"name":"special:quake"},"monitor":0}]'
"$HOME/.local/bin/glaze-quake"
test "$(grep -c '^kitty ' "$COMMAND_LOG" || :)" -eq 0
grep -Fx 'hl.dsp.focus({ monitor = "DP-1" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.resize({ x = 1152, y = 486, relative = false, window = "address:0xabc" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.move({ x = 5108, y = 848, relative = false, window = "address:0xabc" })' "$COMMAND_LOG"

: > "$COMMAND_LOG"
export CLIENTS_JSON='[{"address":"0xabc","class":"quake-kitty","workspace":{"name":"1"},"monitor":0}]'
"$HOME/.local/bin/glaze-quake"
grep -Fx 'hl.dsp.window.move({ workspace = "special:quake", follow = false, window = "address:0xabc" })' "$COMMAND_LOG"
test "$(grep -c '^kitty ' "$COMMAND_LOG" || :)" -eq 0

: > "$COMMAND_LOG"
export MONITORS_JSON='[{"id":0,"name":"DP-2","x":2404,"y":381,"width":2560,"height":1440,"focused":false,"specialWorkspace":{"name":"special:quake"}},{"id":2,"name":"DP-1","x":4964,"y":768,"width":1440,"height":900,"focused":true,"specialWorkspace":{"name":""}}]'
"$HOME/.local/bin/glaze-quake"
grep -Fx 'hl.dsp.focus({ monitor = "DP-2" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.workspace.toggle_special("quake")' "$COMMAND_LOG"
test "$(tail -1 "$COMMAND_LOG")" = 'hl.dsp.focus({ monitor = "DP-1" })'
test "$(grep -c '^kitty ' "$COMMAND_LOG" || :)" -eq 0
echo 'PASS: Quake spawns once, toggles, and selects pointer monitor'
