#!/usr/bin/env bash
set -euo pipefail
# Bars reserve their own footprint: 4px on the side monitors, 24px on the
# main monitor so the under-bar gap matches DP-2's bottom margin. No external
# top gap may add space between a bar and the windows below it.
qml="$HOME/.config/quickshell/StatusbarApp/StatusbarWindow.qml"
hypr="$HOME/.config/hypr/hyprland.lua"
pad="$HOME/.config/hypr/bar_padding.lua"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# Main bar: reserve the pill's lower edge plus 4px, not reservedHeight - gap.
grep -q 'pillFootprint: reservedHeight / 2 + (barHeight + 10) / 2' "$qml" \
  || fail "main bar must compute the pill's lower edge"
grep -q 'exclusiveZone: (barEnabled && !autohide) ? pillFootprint + 20 : 0' "$qml" \
  || fail "main bar must reserve 20px below the pill"
grep -q 'reservedHeight - windowGap' "$qml" \
  && fail "main bar must not subtract the old window gap"

# Vitreus regenerates 76/16px top gaps; a stable override loaded after it must
# zero only the top edge, leaving the other gaps alone.
[[ -f "$pad" ]] || fail "bar_padding.lua override missing"
grep -q 'bar_padding' "$hypr" || fail "hyprland.lua must load bar_padding.lua"
grep -qE 'top = [1-9]' "$pad" && fail "bar padding override must zero the top gap"
grep -q 'm\[DP-2\]' "$pad" || fail "override must cover DP-2"
grep -q 'm\[DP-2\].*bottom = 21' "$pad" \
  || fail "DP-2 bottom margin must be 21px to match the bar"
grep -q 'm\[HDMI-A-2\]' "$pad" || fail "override must cover HDMI-A-2"
grep -q 'm\[DP-1\]' "$pad" || fail "override must cover DP-1"
printf 'PASS: bar padding matches the bottom margin\n'
