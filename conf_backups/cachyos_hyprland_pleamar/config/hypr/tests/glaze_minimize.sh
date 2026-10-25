#!/usr/bin/env bash
set -euo pipefail
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
cat > "$test_dir/hyprctl" <<'FAKE'
#!/usr/bin/env bash
case "$1 $2" in
    'activewindow -j') printf '%s\n' "$ACTIVE_JSON" ;;
    'clients -j') printf '%s\n' "$CLIENTS_JSON" ;;
    'monitors -j') printf '%s\n' "$MONITORS_JSON" ;;
    'dispatch '*) printf '%s\n' "$2" >> "$COMMAND_LOG" ;;
    *) echo "Unexpected hyprctl: $*" >&2; exit 1 ;;
esac
FAKE
chmod +x "$test_dir/hyprctl"
export PATH="$test_dir:$PATH" XDG_RUNTIME_DIR="$test_dir" COMMAND_LOG="$test_dir/commands"
export MONITORS_JSON='[{"id":0,"name":"DP-2","focused":false,"activeWorkspace":{"id":1},"specialWorkspace":{"name":""}},{"id":1,"name":"HDMI-A-2","focused":true,"activeWorkspace":{"id":2},"specialWorkspace":{"name":""}},{"id":2,"name":"DP-1","focused":false,"activeWorkspace":{"id":7},"specialWorkspace":{"name":""}}]'
export CLIENTS_JSON='[]'
export ACTIVE_JSON='{"address":"0xaaa","workspace":{"id":2,"name":"2"},"monitor":1}'
minimize="$HOME/.local/bin/glaze-minimize"

"$minimize" hide
grep -Fx 'hl.dsp.window.move({ workspace = "special:minimized", follow = false, window = "address:0xaaa" })' "$COMMAND_LOG"
grep -Fx $'0xaaa\t2' "$test_dir/glaze-minimized.tsv"
export ACTIVE_JSON='{"address":"0xbbb","workspace":{"id":7,"name":"7"},"monitor":2}'
"$minimize" hide
grep -Fx $'0xbbb\t7' "$test_dir/glaze-minimized.tsv"

: > "$COMMAND_LOG"
export CLIENTS_JSON='[{"address":"0xaaa","workspace":{"name":"special:minimized"},"monitor":1},{"address":"0xbbb","workspace":{"name":"special:minimized"},"monitor":2},{"address":"0xccc","workspace":{"name":"special:minimized"},"monitor":0}]'
export MONITORS_JSON='[{"id":0,"name":"DP-2","focused":false,"activeWorkspace":{"id":1},"specialWorkspace":{"name":""}},{"id":1,"name":"HDMI-A-2","focused":true,"activeWorkspace":{"id":2},"specialWorkspace":{"name":""}},{"id":2,"name":"DP-1","focused":false,"activeWorkspace":{"id":7},"specialWorkspace":{"name":"special:minimized"}}]'
"$minimize" restore-all
grep -Fx 'hl.dsp.window.move({ workspace = "2", follow = false, window = "address:0xaaa" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.move({ workspace = "7", follow = false, window = "address:0xbbb" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.move({ workspace = "1", follow = false, window = "address:0xccc" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.workspace.toggle_special("minimized")' "$COMMAND_LOG"
toggle_line=$(grep -Fn 'hl.dsp.workspace.toggle_special("minimized")' "$COMMAND_LOG" | cut -d: -f1)
focus_line=$(grep -Fn 'hl.dsp.focus({ monitor = "HDMI-A-2" })' "$COMMAND_LOG" | cut -d: -f1)
test "$focus_line" -gt "$toggle_line"
test ! -s "$test_dir/glaze-minimized.tsv"
echo 'PASS: minimize records origins and restores all without an overlay'
