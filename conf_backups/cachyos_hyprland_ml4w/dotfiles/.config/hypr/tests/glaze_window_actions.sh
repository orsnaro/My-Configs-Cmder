#!/usr/bin/env bash
set -euo pipefail
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
cat > "$test_dir/hyprctl" <<'FAKE'
#!/usr/bin/env bash
case "$1" in
    activewindow) printf '%s\n' "$ACTIVE_JSON" ;;
    monitors) printf '%s\n' "$MONITORS_JSON" ;;
    dispatch)
        if [[ $2 == function* ]]; then
            # Transport/callback failures are not layout capability detection.
            if [[ ${DISPATCH_FAIL:-0} == 1 ]]; then exit 1; fi
            export DISPATCH_EXPR="$2"
            export TEST_FOCUS_ADDRESS="${DISPATCH_FOCUS_ADDRESS:-$(jq -r '.address' <<< "$ACTIVE_JSON")}" \
                TEST_FOCUS_WORKSPACE="${DISPATCH_FOCUS_WORKSPACE:-$(jq -r '.workspace.id' <<< "$ACTIVE_JSON")}" 
            lua - <<'LUA' >> "$COMMAND_LOG"
hl = {
    get_active_window = function()
        local address = os.getenv("TEST_FOCUS_ADDRESS")
        if address == "nil" then return nil end
        return { address = address, workspace = {
            id = tonumber(os.getenv("TEST_FOCUS_WORKSPACE")),
            tiled_layout = os.getenv("TEST_TILED_LAYOUT") or "dwindle",
        } }
    end,
    dispatch = function(action) return action() end,
    dsp = {
        layout = function(name)
            return function()
                local log = assert(io.open(os.getenv("LAYOUT_LOG"), "a"))
                log:write(name .. "\n")
                log:close()
                if os.getenv("LAYOUT_REJECT") == "1" then return { ok = false } end
                print('hl.dsp.layout("' .. name .. '")')
                return { ok = true }
            end
        end,
        window = {
            swap = function(options)
                return function()
                    print('hl.dsp.window.swap({ direction = "' .. options.direction .. '" })')
                    return { ok = true }
                end
            end,
        },
    },
}
local callback = assert(load("return " .. os.getenv("DISPATCH_EXPR"), "pair-dispatch"))()
hl.dispatch(callback)
LUA
        else
            printf '%s\n' "$2" >> "$COMMAND_LOG"
        fi
        ;;
    clients) if [[ ${CLIENTS_FAIL:-0} == 1 ]]; then echo 'clients fail' >&2; exit 1; fi; printf '%s\n' "${CLIENTS_JSON:-[]}" ;;
    *) echo "Unexpected hyprctl: $*" >&2; exit 1 ;;
esac
FAKE
chmod +x "$test_dir/hyprctl"
export PATH="$test_dir:$PATH" COMMAND_LOG="$test_dir/dispatches" LAYOUT_LOG="$test_dir/layouts"
export MONITORS_JSON='[{"id":0,"name":"DP-2","x":2404,"y":381,"width":2560,"height":1440},{"id":1,"name":"HDMI-A-2","x":1038,"y":768,"width":1366,"height":768},{"id":2,"name":"DP-1","x":4964,"y":768,"width":1440,"height":900}]'
export ACTIVE_JSON='{"address":"0xabc","class":"kitty","monitor":0,"floating":false,"workspace":{"id":1,"name":"1"}}'
export CLIENTS_JSON='[]'

move="${MOVE_SCRIPT:-$HOME/.local/bin/glaze-move-window}"
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
: > "$COMMAND_LOG"

TOGGLE='hl.dsp.layout("togglesplit")'
SWAP='hl.dsp.layout("swapsplit")'
BATCH=$'hl.dsp.layout("togglesplit")\nhl.dsp.layout("swapsplit")'
mkclient() {
    local fullscreen=$8
    case "$fullscreen" in false) fullscreen=0 ;; true) fullscreen=1 ;; esac
    printf '{"address":"%s","at":[%s],"size":[%s],"workspace":{"id":%s,"name":"%s"},"monitor":0,"floating":%s,"mapped":%s,"hidden":%s,"fullscreen":%s,"grouped":%s,"class":"kitty"}' "$1" "$2" "$3" "$4" "$4" "$5" "$6" "$7" "$fullscreen" "$9"
}
SIDE=$(printf '[%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false 0 '[]')" "$(mkclient 0xbbb '800,0' '800,600' 1 false true false 0 '[]')")
STACK=$(printf '[%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false 0 '[]')" "$(mkclient 0xbbb '0,600' '800,600' 1 false true false 0 '[]')")
expect_one() {
    local actual
    actual=$(< "$COMMAND_LOG")
    if [[ $actual != "$1" ]]; then
        printf 'FAIL: expected dispatches:\n%s\nActual:\n%s\n' "$1" "$actual" >&2
        exit 1
    fi
    : > "$COMMAND_LOG"
}
active_for() { printf '{"address":"%s","class":"kitty","monitor":0,"floating":false,"workspace":{"id":1,"name":"1"}}' "$1"; }

export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" up; expect_one "$TOGGLE"
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one "$BATCH"
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" up; expect_one "$BATCH"
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" down; expect_one "$TOGGLE"
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" left; expect_one "$TOGGLE"
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" right; expect_one "$BATCH"
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" left; expect_one "$BATCH"
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" right; expect_one "$TOGGLE"

# Execute the emitted callback, not just its text: stale focus must do nothing.
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"
export DISPATCH_FOCUS_ADDRESS=0xccc; "$move" down; expect_one ''
export DISPATCH_FOCUS_ADDRESS=nil; "$move" down; expect_one ''
unset DISPATCH_FOCUS_ADDRESS
export DISPATCH_FOCUS_WORKSPACE=2; "$move" down; expect_one ''
unset DISPATCH_FOCUS_WORKSPACE

export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" left; expect_one 'hl.dsp.window.move({ direction = "l" })'
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" up; expect_one 'hl.dsp.window.move({ direction = "u" })'
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" right; expect_one 'hl.dsp.window.move({ direction = "r" })'
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'

# Moving toward the partner exchanges slots, without removing/reinserting tiles.
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one "$SWAP"
export CLIENTS_JSON="$STACK" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" up; expect_one "$SWAP"
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" right; expect_one "$SWAP"
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" left; expect_one "$SWAP"

# Unsupported layout messages return {ok=false}, not a failed hyprctl process.
# Master must swap directly, without trying any dwindle-only messages.
export TEST_TILED_LAYOUT=master LAYOUT_REJECT=1
: > "$LAYOUT_LOG"
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xbbb)"
"$move" left; expect_one 'hl.dsp.window.swap({ direction = "l" })'
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"
"$move" right; expect_one 'hl.dsp.window.swap({ direction = "r" })'
"$move" down; expect_one 'hl.dsp.window.swap({ direction = "d" })'
[[ ! -s "$LAYOUT_LOG" ]] || { echo 'FAIL: master received dwindle-only messages' >&2; exit 1; }
export DISPATCH_FOCUS_ADDRESS=0xccc; "$move" down; expect_one ''
unset DISPATCH_FOCUS_ADDRESS
export DISPATCH_FOCUS_WORKSPACE=2; "$move" down; expect_one ''
unset DISPATCH_FOCUS_WORKSPACE
for layout in scrolling unknown; do
    export TEST_TILED_LAYOUT="$layout"
    "$move" right; expect_one 'hl.dsp.window.swap({ direction = "r" })'
done
unset TEST_TILED_LAYOUT LAYOUT_REJECT

# An IPC failure must not cause a second, unguarded swap on a different focus.
export DISPATCH_FAIL=1
if "$move" right; then echo 'FAIL: IPC failure must be reported' >&2; exit 1; fi
expect_one ''
unset DISPATCH_FAIL

UNEQUAL_STACK=$(printf '[%s,%s]' "$(mkclient 0xaaa '0,0' '800,900' 1 false true false 0 '[]')" "$(mkclient 0xbbb '0,900' '800,300' 1 false true false 0 '[]')")
UNEQUAL_SIDE=$(printf '[%s,%s]' "$(mkclient 0xaaa '0,0' '1200,600' 1 false true false 0 '[]')" "$(mkclient 0xbbb '1200,0' '400,600' 1 false true false 0 '[]')")
export CLIENTS_JSON="$UNEQUAL_STACK" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one "$SWAP"
export CLIENTS_JSON="$UNEQUAL_STACK" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" up; expect_one "$SWAP"
export CLIENTS_JSON="$UNEQUAL_SIDE" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" right; expect_one "$SWAP"
export CLIENTS_JSON="$UNEQUAL_SIDE" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" left; expect_one "$SWAP"
export DISPATCH_FOCUS_ADDRESS=0xccc; "$move" left; expect_one ''
unset DISPATCH_FOCUS_ADDRESS

export CLIENTS_JSON="$(printf '[%s,%s,%s,%s,%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false false '[]')" "$(mkclient 0xbbb '800,0' '800,600' 1 false true false false '[]')" "$(mkclient 0xccc '0,0' '400,300' 1 true true false false '[]')" "$(mkclient 0xddd '0,0' '800,600' 1 false false false false '[]')" "$(mkclient 0xeee '0,0' '800,600' 1 false true true false '[]')" "$(mkclient 0xfff '0,0' '800,600' 2 false true false false '[]')")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one "$BATCH"

export CLIENTS_JSON="$(printf '[%s,%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false false '[]')" "$(mkclient 0xbbb '800,0' '800,600' 1 false true false false '[]')" "$(mkclient 0xccc '0,600' '800,300' 1 false true false false '["0xaaa"]')")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$(printf '[%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false true '[]')" "$(mkclient 0xbbb '800,0' '800,600' 1 false true false false '[]')")" ACTIVE_JSON="$(active_for 0xbbb)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$(printf '[%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false false '["0xbbb"]')" "$(mkclient 0xbbb '800,0' '800,600' 1 false true false false '[]')")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$(printf '[%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false false '[]')")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$(printf '[%s,%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false false '[]')" "$(mkclient 0xbbb '800,0' '800,600' 1 false true false false '[]')" "$(mkclient 0xccc '0,600' '800,300' 1 false true false false '[]')")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xzzz)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON='not-json' ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_FAIL=1 CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'; unset CLIENTS_FAIL
export CLIENTS_JSON="$(printf '[%s,%s]' "$(mkclient 0xaaa '0,0' '800,600' 1 false true false false '[]')" "$(mkclient 0xbbb '900,700' '800,600' 1 false true false false '[]')")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$SIDE" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" monitor right; expect_one 'hl.dsp.window.move({ monitor = "DP-1", follow = true })'
export CLIENTS_JSON="$SIDE" ACTIVE_JSON='{"address":"0xaaa","class":"kitty","monitor":0,"floating":true,"workspace":{"id":1,"name":"1"}}'; "$move" down; expect_one 'hl.dsp.window.move({ x = 0, y = 216, relative = true })'

export CLIENTS_JSON="$SIDE" ACTIVE_JSON='{}'; "$move" down; expect_one ''
export CLIENTS_JSON='[]' ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$(jq '.[1].size = [0, 600]' <<< "$SIDE")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'
export CLIENTS_JSON="$(jq '.[1].at = [400, 0]' <<< "$SIDE")" ACTIVE_JSON="$(active_for 0xaaa)"; "$move" down; expect_one 'hl.dsp.window.move({ direction = "d" })'

echo 'PASS: directional pairs, focus guards, native/floating moves, monitor transfers, and resize'
