#!/usr/bin/env bash
set -euo pipefail
# Slim side bars contract: thin workspaces+clock bars on both side monitors.
app="$HOME/.config/quickshell/StatusbarApp"
shell="$HOME/.config/quickshell/shell.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

[[ -f "$app/SlimBarWindow.qml" ]] || fail "SlimBarWindow.qml missing"
grep -q 'HDMI-A-2' "$shell" || fail "shell must place a slim bar on HDMI-A-2"
grep -q 'DP-1' "$shell" || fail "shell must place a slim bar on DP-1"
grep -q 'SlimBarWindow' "$shell" || fail "shell must instantiate SlimBarWindow"
# A missing/unplugged side output hides its bar instead of duplicating center.
grep -q 'visible:' "$app/SlimBarWindow.qml" || fail "slim bar must gate visibility on screen lookup"
# Task 2: layout + volume on the slim pill, reused modules, still no pollers.
grep -q 'KeyboardLayoutModule' "$app/SlimBarWindow.qml" || fail "slim bar must show keyboard layout"
grep -q 'VolumeModule' "$app/SlimBarWindow.qml" || fail "slim bar must show volume"
grep -q 'hypr-sysinfo' "$app/SlimBarWindow.qml" && fail "slim bar must not poll sysinfo"
grep -q 'Timer' "$app/SlimBarWindow.qml" && fail "slim bar must not run timers"
# Task 3: shared calendar under each side clock, clamped on screen.
grep -q 'CalendarPanel' "$app/SlimBarWindow.qml" || fail "slim bar must host the shared calendar"
grep -q 'Math.max(8,' "$app/SlimBarWindow.qml" || fail "slim calendar must clamp on screen"
# Task 5: per-monitor workspaces + center pill styling.
grep -q 'monitorName' "$app/WorkspacesModule.qml" || fail "workspaces must support per-monitor filtering"
grep -q 'monitorName' "$app/SlimBarWindow.qml" || fail "slim bar must pass its screen into workspaces"
grep -q 'Gradient' "$app/SlimBarWindow.qml" || fail "slim pill must share the center gradient border"
grep -q 'RectangularShadow' "$app/SlimBarWindow.qml" || fail "slim pill must share the center shadow"
grep -q 'topMargin: 10' "$app/SlimBarWindow.qml" || fail "slim pill sits 10px from the top edge"
# Gamemode sets gaps_out=0, so windows tile exactly at the reserved edge.
# The pill is drawn 10px below the panel top; the reserved strip must cover
# that margin plus 4px of clear padding below the pill, or its lower edge
# overlaps (or touches) every side-monitor window.
bar_height=$(grep -oE 'property int barHeight: [0-9]+' "$app/SlimBarWindow.qml" | head -1 | awk '{print $NF}' || true)
top_margin=$(grep -oE 'anchors\.topMargin: [0-9]+' "$app/SlimBarWindow.qml" | head -1 | awk '{print $2}' || true)
reserve=$(grep -oE 'exclusiveZone: barHeight \+ [0-9]+ \+ [0-9]+' "$app/SlimBarWindow.qml" | head -1 || true)
[[ -n "$bar_height" && -n "$top_margin" && -n "$reserve" ]] \
  || fail "slim bar reserve must cover pill top margin plus 4px padding"
margin_part=$(printf '%s\n' "$reserve" | awk '{print $4}')
padding_part=$(printf '%s\n' "$reserve" | awk '{print $6}')
[[ "$margin_part" == "$top_margin" ]] \
  || fail "slim bar reserve margin ($margin_part) must match pill top margin ($top_margin)"
[[ "$padding_part" == "4" ]] \
  || fail "slim bar must leave 4px padding below the pill (got $padding_part)"
[[ $((bar_height + top_margin + padding_part)) -eq 50 ]] \
  || fail "slim bar reserved strip must total 50px"
# Task 4: slim screens come from the slimBars setting, both sides by default.
grep -q 'slimBars' "$shell" || fail "shell must drive slim bars from the slimBars setting"
grep -q 'target: "slimbars"' "$shell" || fail "shell must expose slimbars reload IPC for live apply"
grep -q 'HDMI-A-2' "$shell" || fail "slimBars default must include HDMI-A-2"
grep -q 'DP-1' "$shell" || fail "slimBars default must include DP-1"
printf 'PASS: slim side bars wired\n'
