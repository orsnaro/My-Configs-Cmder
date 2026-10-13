#!/usr/bin/env bash
set -euo pipefail
# Slideshow single-instance + enabled-persistence contracts for ml4w-wallpaper-automation.
auto="$HOME/.config/ml4w/scripts/ml4w-wallpaper-automation"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q -- "$2" "$1" || fail "$3"; }

need "$auto" "wallpaper-automation.pid" "automation must use a pid file"
need "$auto" -- "--status" "automation must support --status"
need "$auto" -- "--start" "automation must support --start"
need "$auto" -- "--stop" "automation must support --stop"
need "$auto" "wallpaper-slideshow" "automation must persist enabled state in settings/wallpaper-slideshow"
need "$auto" "kill -0" "automation must check liveness, not just flag existence"

# ---- Isolated functional tests ----
sandbox() {
    local home; home=$(mktemp -d /tmp/opencode/wallpaper-auto-test-XXXXXX)
    mkdir -p "$home/.config/ml4w/scripts" "$home/.config/ml4w/settings" "$home/.cache/ml4w/hyprland-dotfiles" "$home/bin"
    printf '300' > "$home/.config/ml4w/settings/wallpaper-automation"
    cat > "$home/.config/ml4w/scripts/ml4w-notification-handler" <<'STUB'
notify_user() { printf 'NOTIFY %s\n' "$*" >> "$AUDIT_LOG"; }
STUB
    cat > "$home/.config/ml4w/scripts/ml4w-wallpaper" <<'STUB'
#!/usr/bin/env bash
printf 'WALLPAPER %s\n' "$*" >> "$AUDIT_LOG"
exit "${WALLPAPER_FAIL:-0}"
STUB
    chmod +x "$home/.config/ml4w/scripts/ml4w-wallpaper"
    cat > "$home/bin/sleep" <<'STUB'
#!/usr/bin/env bash
printf 'SLEEP %s\n' "$*" >> "$AUDIT_LOG"
if [[ "${1:-}" =~ ^[0-9]+$ ]] && (( $1 >= 100 )); then
    n=$(grep -c "^SLEEP $1\$" "$AUDIT_LOG")
    if (( n >= 5000 )); then kill -TERM "$PPID"; fi
fi
exit 0
STUB
    chmod +x "$home/bin/sleep"
    printf '%s' "$home"
}

auto_env() { printf 'HOME=%s PATH=%s/bin:/usr/bin:/bin AUDIT_LOG=%s/calls.log' "$1" "$1" "$1"; }

wait_for() {
    local deadline=$((SECONDS + 10))
    while ! grep -q -- "$2" "$1/calls.log" 2>/dev/null; do
        (( SECONDS < deadline )) || return 1
        /bin/sleep 0.05
    done
}

stop_bg() { # $1 = home; never fail the suite on cleanup
    env $(auto_env "$1") timeout 10 bash "$auto" --stop >/dev/null 2>&1 || true
}

hd() { printf '%s/.cache/ml4w/hyprland-dotfiles' "$1"; }
pidfile_of() { printf '%s/wallpaper-automation.pid' "$(hd "$1")"; }
enabled_of() { printf '%s/.config/ml4w/settings/wallpaper-slideshow' "$1"; }

# Case A: fresh start -> pid file, enabled true, ordered loop, status, clean stop.
h=$(sandbox); : > "$h/calls.log"
env $(auto_env "$h") timeout 10 bash "$auto" --start >>"$h/cli.log" 2>&1 &
loop_pid=$!
wait_for "$h" "^WALLPAPER --random$" || { stop_bg "$h"; fail "fresh start never called ml4w-wallpaper"; }
pidfile=$(pidfile_of "$h")
[[ -f "$pidfile" ]] || { stop_bg "$h"; fail "fresh start must create pid file"; }
recorded=$(cat "$pidfile")
kill -0 "$recorded" 2>/dev/null || { stop_bg "$h"; fail "pid file must hold a live PID"; }
tr '\0' ' ' < "/proc/$recorded/cmdline" 2>/dev/null | grep -q "ml4w-wallpaper-automation" || { stop_bg "$h"; fail "pid file must hold the automation loop"; }
[[ "$(cat "$(enabled_of "$h")")" == "true" ]] || { stop_bg "$h"; fail "start must persist enabled=true"; }
wait_for "$h" "^SLEEP 300$" || { stop_bg "$h"; fail "loop must sleep 300 between changes"; }
seq=$(grep -E '^(WALLPAPER|SLEEP) ' "$h/calls.log" | head -4 | tr '\n' ';')
[[ "$seq" == "WALLPAPER --random;SLEEP 300;WALLPAPER --random;SLEEP 300;" ]] || { stop_bg "$h"; fail "loop order wrong: $seq"; }
env $(auto_env "$h") timeout 10 bash "$auto" --status >/dev/null 2>&1 || { stop_bg "$h"; fail "--status must exit 0 while running"; }
env $(auto_env "$h") timeout 10 bash "$auto" --stop >>"$h/cli.log" 2>&1 || { stop_bg "$h"; fail "--stop must exit 0"; }
wait "$loop_pid" 2>/dev/null || true
[[ ! -f "$pidfile" ]] || fail "stop must remove pid file"
[[ "$(cat "$(enabled_of "$h")")" == "false" ]] || fail "stop must persist enabled=false"
env $(auto_env "$h") timeout 10 bash "$auto" --status >/dev/null 2>&1 && fail "--status must exit nonzero after stop"

# Case B: duplicate start must not spawn a second loop.
h=$(sandbox); : > "$h/calls.log"
env $(auto_env "$h") timeout 10 bash "$auto" --start >>"$h/cli.log" 2>&1 &
loop_pid=$!
wait_for "$h" "^WALLPAPER --random$" || { stop_bg "$h"; fail "case B: loop never started"; }
/bin/sleep 0.2
p1=$(cat "$(pidfile_of "$h")")
env $(auto_env "$h") timeout 10 bash "$auto" --start >>"$h/cli.log" 2>&1 || { stop_bg "$h"; fail "duplicate --start must exit 0"; }
[[ "$(cat "$(pidfile_of "$h")")" == "$p1" ]] || { stop_bg "$h"; fail "duplicate --start must keep the original loop"; }
stop_bg "$h"; wait "$loop_pid" 2>/dev/null || true

# Case C: stale pid file recovers.
h=$(sandbox); /bin/sleep 0.01 & dead=$!; wait "$dead" 2>/dev/null || true
printf '%s' "$dead" > "$(pidfile_of "$h")"; printf 'true' > "$(enabled_of "$h")"
: > "$h/calls.log"
env $(auto_env "$h") timeout 10 bash "$auto" --start >>"$h/cli.log" 2>&1 &
loop_pid=$!
wait_for "$h" "^WALLPAPER --random$" || { stop_bg "$h"; fail "stale pid must not block a fresh start"; }
[[ "$(cat "$(pidfile_of "$h")")" != "$dead" ]] || { stop_bg "$h"; fail "stale pid must be replaced"; }
stop_bg "$h"; wait "$loop_pid" 2>/dev/null || true

# Case D: legacy empty marker migrates to enabled and is removed.
h=$(sandbox); touch "$(hd "$h")/wallpaper-automation"; : > "$h/calls.log"
env $(auto_env "$h") timeout 10 bash "$auto" --start >>"$h/cli.log" 2>&1 &
loop_pid=$!
wait_for "$h" "^WALLPAPER --random$" || { stop_bg "$h"; fail "legacy marker must still allow start"; }
[[ ! -e "$(hd "$h")/wallpaper-automation" ]] || { stop_bg "$h"; fail "legacy marker must be migrated away"; }
[[ "$(cat "$(enabled_of "$h")")" == "true" ]] || { stop_bg "$h"; fail "legacy marker must migrate to enabled=true"; }
stop_bg "$h"; wait "$loop_pid" 2>/dev/null || true

# Case E: failing wallpaper child does not kill the loop.
h=$(sandbox); : > "$h/calls.log"
env $(auto_env "$h") WALLPAPER_FAIL=1 timeout 10 bash "$auto" --start >>"$h/cli.log" 2>&1 &
loop_pid=$!
wait_for "$h" "^SLEEP 300$" || { stop_bg "$h"; fail "loop must sleep even when wallpaper fails"; }
n=$(grep -c '^WALLPAPER --random$' "$h/calls.log")
(( n >= 2 )) || { stop_bg "$h"; fail "loop must retry after wallpaper failure (calls=$n)"; }
stop_bg "$h"; wait "$loop_pid" 2>/dev/null || true

# Case G: two simultaneous starts must leave exactly one loop.
h=$(sandbox); : > "$h/calls.log"
env $(auto_env "$h") timeout 10 bash "$auto" --start >"$h/a.log" 2>&1 &
env $(auto_env "$h") timeout 10 bash "$auto" --start >"$h/b.log" 2>&1 &
deadline=$((SECONDS + 8))
until { grep -q 'already' "$h/a.log" || grep -q 'already' "$h/b.log"; } 2>/dev/null; do
    (( SECONDS < deadline )) || break
    /bin/sleep 0.05
done
starts=$(( $(grep -c 'Start wallpaper automation script' "$h/a.log" || true) + $(grep -c 'Start wallpaper automation script' "$h/b.log" || true) + 0 ))
(( starts == 1 )) || { stop_bg "$h"; fail "exactly one concurrent start must enter the loop (starts=$starts)"; }
[[ -f "$(pidfile_of "$h")" ]] || { stop_bg "$h"; fail "concurrent start must leave a pid file"; }
stop_bg "$h"

# Case F: invalid interval falls back to 300.
h=$(sandbox); printf 'abc' > "$h/.config/ml4w/settings/wallpaper-automation"; : > "$h/calls.log"
env $(auto_env "$h") timeout 10 bash "$auto" --start >>"$h/cli.log" 2>&1 &
loop_pid=$!
wait_for "$h" "^SLEEP 300$" || { stop_bg "$h"; fail "invalid interval must fall back to 300"; }
stop_bg "$h"; wait "$loop_pid" 2>/dev/null || true

printf 'PASS: slideshow single-instance and persistence honored\n'
