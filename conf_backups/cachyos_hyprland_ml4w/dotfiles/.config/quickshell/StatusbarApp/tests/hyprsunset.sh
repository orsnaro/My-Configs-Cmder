#!/usr/bin/env bash
set -euo pipefail
# Night controls route through the selected desktop stack.
app="$HOME/.config/quickshell/StatusbarApp"
conf="$HOME/.config/hypr/hyprsunset.conf"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -f "$conf" ]] || fail "hyprsunset.conf missing"
grep -Eq '^[[:space:]]*profile[[:space:]]*\{' "$conf" && fail "backend must not run a competing profile schedule" || true
need "$conf" "night.json" "backend config must document the shared saved state"

auto="$HOME/.mydotfiles/com.ml4w.dotfiles.stable/.config/hypr/conf/autostart.lua"
grep -Eq '^[[:space:]]*hl\.exec_cmd\("hyprsunset' "$auto" && fail "Vitreus alone must start its backend" || true
need "$auto" "desktop-stack.*resume" "autostart must resume the selected settings owner"

# No bar icons anywhere: neither center nor slim bars reference it.
grep '"right"' "$app/StatusbarWindow.qml" | grep -q '"hyprsunset"' && fail "center bar must not list hyprsunset" || true
grep '"right"' "$app/config.json" | grep -q '"hyprsunset"' && fail "config doc must not list hyprsunset" || true
grep -q "Hyprsunset" "$app/SlimBarWindow.qml" && fail "slim bars must not host hyprsunset" || true
[[ ! -f "$app/HyprsunsetModule.qml" ]] || fail "HyprsunsetModule.qml must be removed"

# Sidebar reads and changes the same state as the keyboard and Waybar.
side="$HOME/.config/quickshell/SidebarApp/SidebarWindow.qml"
need "$side" "Blue Light Filter" "sidebar must keep the Blue Light Filter switch"
need "$side" "Shared with Vitreus" "sidebar must identify the shared settings"
need "$side" "ml4w-toggle-hyprsunset status" "sidebar must query the shared state"
need "$side" 'checked ? "on" : "off"' "sidebar must use absolute shared controls"

# Pleamar keeps saved-state controls; QS uses its separately gated backend.
toggle="$HOME/.config/ml4w/scripts/ml4w-toggle-hyprsunset"
need "$toggle" "emit night_toggle" "toggle must use the shared event"
need "$toggle" "emit night_set 0" "Off must use the shared absolute setter"
need "$toggle" "desktop_stack_is_qs" "QS backend operations must be mode-gated"

printf 'PASS: night-mode controls share Vitreus state\n'
