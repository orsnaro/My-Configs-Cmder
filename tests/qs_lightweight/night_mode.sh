#!/usr/bin/env bash
set -euo pipefail
# Current mode-routed night controls; no live activation.
app="$HOME/.config/quickshell/StatusbarApp"
conf="$HOME/.config/hypr/hyprsunset.conf"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -f "$conf" ]] || fail "hyprsunset.conf missing"
grep -Eq '^[[:space:]]*profile[[:space:]]*\{' "$conf" && fail "backend must not run a competing profile schedule" || true
need "$conf" "night.json" "backend config must document the shared saved state"

auto="$HOME/.config/hypr/conf/autostart.lua"
need "$auto" "desktop-stack.*resume" "autostart must resume the selected settings owner"

grep '"right"' "$app/StatusbarWindow.qml" | grep -q '"hyprsunset"' && fail "bar must not list hyprsunset" || true
grep -q "Hyprsunset" "$app/SlimBarWindow.qml" && fail "slim bars must not host hyprsunset" || true

side="$HOME/.config/quickshell/SidebarApp/SidebarWindow.qml"
need "$side" "ml4w-toggle-hyprsunset status" "sidebar must query the routed state"
need "$side" 'checked ? "on" : "off"' "sidebar must use absolute controls"
toggle="$HOME/.config/ml4w/scripts/ml4w-toggle-hyprsunset"
need "$toggle" "emit night_toggle" "Pleamar toggle must use the shared event"
need "$toggle" "emit night_set 0" "Pleamar Off must use the shared absolute setter"
need "$toggle" "desktop_stack_is_qs" "QS backend operations must be mode-gated"
printf 'PASS: mode-routed night controls\n'
