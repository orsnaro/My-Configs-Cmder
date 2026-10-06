#!/usr/bin/env bash
set -euo pipefail
# Hyprsunset contract: sidebar-only switch. ON = schedule armed, OFF = filter cleared + schedule off.
app="$HOME/.config/quickshell/StatusbarApp"
conf="$HOME/.config/hypr/hyprsunset.conf"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -f "$conf" ]] || fail "hyprsunset.conf missing"
need "$conf" "time *= *00:00" "schedule must start warm at 00:00"
need "$conf" "temperature *= *5000" "night profile must use 5000K"
need "$conf" "time *= *07:00" "schedule must switch at 07:00"
need "$conf" "identity *= *1" "07:00 profile must use identity off state"

auto="$HOME/.mydotfiles/com.ml4w.dotfiles.stable/.config/hypr/conf/autostart.lua"
grep -q "hyprsunset" "$auto" || fail "autostart.lua must launch hyprsunset"

# No bar icons anywhere: neither center nor slim bars reference it.
grep '"right"' "$app/StatusbarWindow.qml" | grep -q '"hyprsunset"' && fail "center bar must not list hyprsunset" || true
grep '"right"' "$app/config.json" | grep -q '"hyprsunset"' && fail "config doc must not list hyprsunset" || true
grep -q "Hyprsunset" "$app/SlimBarWindow.qml" && fail "slim bars must not host hyprsunset" || true
[[ ! -f "$app/HyprsunsetModule.qml" ]] || fail "HyprsunsetModule.qml must be removed"

# Sidebar switch documents the auto schedule and clears the filter on OFF.
side="$HOME/.config/quickshell/SidebarApp/SidebarWindow.qml"
need "$side" "Blue Light Filter" "sidebar must keep the Blue Light Filter switch"
need "$side" "00:00" "sidebar must note the 00:00 start"
need "$side" "07:00" "sidebar must note the 07:00 end"
need "$side" "hyprsunset identity" "sidebar OFF must reset filter via hyprctl hyprsunset identity"

# Keybinding toggle shares the same OFF-clears-filter behavior.
need "$HOME/.config/ml4w/scripts/ml4w-toggle-hyprsunset" "hyprsunset identity" "toggle-off must reset filter via hyprctl hyprsunset identity"

printf 'PASS: hyprsunset sidebar-only wired\n'
