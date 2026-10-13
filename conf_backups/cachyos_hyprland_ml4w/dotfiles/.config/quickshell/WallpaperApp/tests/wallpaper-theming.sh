#!/usr/bin/env bash
set -euo pipefail
# Theming preference contract + isolated behavior for ml4w-wallpaper.
# Style follows StatusbarApp/tests/sysinfo.sh (fail/need helpers).
wallpaper="$HOME/.config/ml4w/scripts/ml4w-wallpaper"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q -- "$2" "$1" || fail "$3"; }

need "$wallpaper" "wallpaper-theming" "ml4w-wallpaper must reference settings/wallpaper-theming"
need "$wallpaper" "--theming" "ml4w-wallpaper must support --theming explicit-on flag"

# ---- Isolated functional tests: temporary HOME, stubbed desktop commands ----
sandbox() {
    local home; home=$(mktemp -d /tmp/opencode/wallpaper-theming-test-XXXXXX)
    mkdir -p "$home/.config/ml4w/settings" "$home/.config/gtk-3.0" "$home/bin"
    printf 'simple' > "$home/.config/ml4w/settings/wallpaper-transition-effect"
    printf 'off' > "$home/.config/ml4w/settings/wallpaper-effect"
    printf '0x0' > "$home/.config/ml4w/settings/blur.sh"
    printf '[Settings]\ngtk-application-prefer-dark-theme=1\n' > "$home/.config/gtk-3.0/settings.ini"
    touch "$home/input.png"
    local name
    for name in awww matugen magick qs swaync-client walker pkill killall pgrep pywalfox notify-send nohup sleep; do
        cat > "$home/bin/$name" <<'STUB'
#!/usr/bin/env bash
printf '%s %s\n' "${0##*/}" "$*" >> "$AUDIT_LOG"
case "${0##*/}" in
  awww) [[ "$1" == "--version" ]] && echo "awww 0.12.1";;
  pgrep) exit 1;;
  matugen) [[ "${AUDIT_FAIL:-}" == "matugen" ]] && exit 1;;
esac
exit 0
STUB
        chmod +x "$home/bin/$name"
    done
    printf '%s' "$home"
}

run_wallpaper() {
    # $1 = sandbox home, remaining args = extra ml4w-wallpaper flags
    local home="$1"; shift
    : > "$home/calls.log"
    local status=0
    HOME="$home" PATH="$home/bin:/usr/bin:/bin" AUDIT_LOG="$home/calls.log" \
        AUDIT_FAIL="${AUDIT_FAIL:-}" bash "$wallpaper" "$home/input.png" "$@" \
        >"$home/out.log" 2>"$home/err.log" || status=$?
    printf '%s' "$status"
}

count_calls() { grep -c "^$2 " "$1/calls.log" 2>/dev/null || true; }

# Case 1: theming file says false, no flags -> matugen must not run.
h=$(sandbox); printf 'false' > "$h/.config/ml4w/settings/wallpaper-theming"
s=$(run_wallpaper "$h")
[[ "$s" == "0" ]] || fail "theming=false run exited $s, want 0"
[[ "$(count_calls "$h" matugen)" == "0" ]] || fail "theming=false must skip matugen"
grep -q "Updating theming skipped" "$h/err.log" || fail "theming=false must log skip"

# Case 2: theming file says false + --theming -> matugen runs once.
h=$(sandbox); printf 'false' > "$h/.config/ml4w/settings/wallpaper-theming"
s=$(run_wallpaper "$h" --theming)
[[ "$s" == "0" ]] || fail "--theming run exited $s, want 0"
[[ "$(count_calls "$h" matugen)" == "1" ]] || fail "--theming must run matugen once"

# Case 3: missing theming file -> created as true, matugen runs.
h=$(sandbox)
s=$(run_wallpaper "$h")
[[ "$s" == "0" ]] || fail "missing-file run exited $s, want 0"
[[ "$(cat "$h/.config/ml4w/settings/wallpaper-theming")" == "true" ]] || fail "missing theming file must default to true"
[[ "$(count_calls "$h" matugen)" == "1" ]] || fail "default theming must run matugen"

# Case 4: matugen fails -> nonzero exit, no success claim.
h=$(sandbox); printf 'true' > "$h/.config/ml4w/settings/wallpaper-theming"
AUDIT_FAIL=matugen s=$(run_wallpaper "$h")
[[ "$s" != "0" ]] || fail "failed matugen must exit nonzero"
grep -q "Matugen updated" "$h/err.log" && fail "failed matugen must not claim update"
unset AUDIT_FAIL

# Case 5: garbage content -> safe fallback to enabled.
h=$(sandbox); printf 'maybe' > "$h/.config/ml4w/settings/wallpaper-theming"
s=$(run_wallpaper "$h")
[[ "$s" == "0" ]] || fail "garbage-file run exited $s, want 0"
[[ "$(count_calls "$h" matugen)" == "1" ]] || fail "garbage theming value must fall back to enabled"

printf 'PASS: wallpaper theming preference honored\n'
