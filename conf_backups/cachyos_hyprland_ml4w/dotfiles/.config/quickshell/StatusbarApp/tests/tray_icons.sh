#!/usr/bin/env bash
set -euo pipefail
# Headless regression test: Blueman tray + menu icons must resolve and render
# through the shell's icon theme, and unrelated tray icons must stay intact.
#
# Quickshell's icon image provider paints a black/purple checkerboard and logs
# `Could not load icon ...` for missing names, while Image.status still reports
# Ready -- so the QML checks hasThemeIcon() and this script rejects the warning.
# The IconTheme pragma is read only at process startup, so it is forwarded to
# this test process via QS_ICON_THEME (the shell reads the same value first).
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
shell="$HOME/.config/quickshell/shell.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

[[ -f "$here/tray_icons.qml" ]] || fail "tray_icons.qml missing"
[[ -f "$shell" ]] || fail "shell.qml missing"

theme="$(sed -n 's|^//@ pragma IconTheme[[:space:]][[:space:]]*\([^[:space:]]*\).*$|\1|p' "$shell" | head -1)"
if [[ -n "$theme" ]]; then
    export QS_ICON_THEME="$theme"
fi
printf 'tray icons: theme=%s\n' "${QS_ICON_THEME:-<qt default>}"

log="$(mktemp "${TMPDIR:-/tmp}/qs-tray-icons.XXXXXX.log")"
trap 'rm -f "$log"' EXIT

set +e
env QT_QPA_PLATFORM=offscreen timeout 60 qs -p "$here/tray_icons.qml" --no-color >"$log" 2>&1
status=$?
set -e

if [[ $status -ne 0 ]]; then
    grep -E 'FAIL:|Could not load icon|PASS:' "$log" >&2 || cat "$log" >&2
    fail "tray icon QML test exited with status $status"
fi
# Checkerboard substitutes are a hard failure even though the image loads.
if grep -q 'Could not load icon' "$log"; then
    grep 'Could not load icon' "$log" >&2
    fail "missing icon rendered as Quickshell's checkerboard placeholder"
fi
if grep -Eq 'QML Image:.*(Cannot open|Error)|Error decoding' "$log"; then
    grep -E 'QML Image:.*(Cannot open|Error)|Error decoding' "$log" >&2
    fail "an icon image failed to load"
fi
if ! grep -q 'PASS: blueman tray/menu icons' "$log"; then
    cat "$log" >&2
    fail "tray icon test did not report PASS"
fi
grep 'PASS: blueman tray/menu icons' "$log"
