#!/usr/bin/env bash
set -euo pipefail
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
cat > "$test_dir/hyprctl" <<'FAKE'
#!/usr/bin/env bash
case "$1 $2" in
    'reload ') echo 'ok' >> "$COMMAND_LOG" ;;
    'configerrors ') printf '\n' ;;
    'clients -j') cat "$CLIENT_FIXTURE" ;;
    'dispatch '*) printf '%s\n' "$2" >> "$COMMAND_LOG" ;;
    *) echo "Unexpected hyprctl: $*" >&2; exit 1 ;;
esac
FAKE
chmod +x "$test_dir/hyprctl"
export PATH="$test_dir:$PATH" COMMAND_LOG="$test_dir/commands" CLIENT_FIXTURE="$test_dir/clients"
cat > "$CLIENT_FIXTURE" <<'JSON'
[
  {"address":"0xa","class":"kitty","title":"terminal","workspace":{"id":2},"floating":true,"fullscreen":0,"mapped":true,"pinned":false},
  {"address":"0xb","class":"brave-browser","title":"browser","workspace":{"id":3},"floating":false,"fullscreen":0,"mapped":true,"pinned":false},
  {"address":"0xc","class":"quake-kitty","title":"quake","workspace":{"id":-99},"floating":true,"fullscreen":0,"mapped":true,"pinned":false},
  {"address":"0xd","class":"steam","title":"Steam","workspace":{"id":1},"floating":false,"fullscreen":2,"mapped":true,"pinned":false},
  {"address":"0xe","class":"dotfiles-floating","title":"ML4W","workspace":{"id":1},"floating":true,"fullscreen":0,"mapped":true,"pinned":false},
  {"address":"0xf","class":"brave-browser","title":"Floating dialog","workspace":{"id":1},"floating":true,"fullscreen":0,"mapped":true,"pinned":false},
  {"address":"0x10","class":"brave-192.168.1.12__-Default","title":"CasaOS","workspace":{"id":1},"floating":false,"fullscreen":0,"mapped":true,"pinned":false},
  {"address":"0x11","class":"brave-192.168.1.12__web_-Default","title":"Jellyfin","workspace":{"id":1},"floating":false,"fullscreen":0,"mapped":true,"pinned":false},
  {"address":"0x12","class":"brave-192.168.1.12__-Default","title":"CasaOS dialog","workspace":{"id":1},"floating":true,"fullscreen":0,"mapped":true,"pinned":false}
]
JSON

"$HOME/.local/bin/glaze-reset"
grep -Fx 'ok' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.float({ action = "unset", window = "address:0xa" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.move({ workspace = "7", follow = false, window = "address:0xa" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.move({ workspace = "8", follow = false, window = "address:0x10" })' "$COMMAND_LOG"
grep -Fx 'hl.dsp.window.move({ workspace = "8", follow = false, window = "address:0x11" })' "$COMMAND_LOG"
if grep -Fq 'address:0x12' "$COMMAND_LOG"; then
    echo 'FAIL: reset must leave the floating CasaOS dialog untouched' >&2
    exit 1
fi
test "$(wc -l < "$COMMAND_LOG")" -eq 5
echo 'PASS: reset reloads, restores a normal terminal, routes CasaOS/Jellyfin to others, skips game/Quake/helpers/dialogs'
