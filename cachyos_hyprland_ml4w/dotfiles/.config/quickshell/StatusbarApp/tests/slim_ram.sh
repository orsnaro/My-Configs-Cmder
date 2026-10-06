#!/usr/bin/env bash
set -euo pipefail
# Slim RAM contract: side bars show same RAM usage as primary, display-only.
app="$HOME/.config/quickshell/StatusbarApp"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

[[ -f "$app/SlimBarWindow.qml" ]] || fail "SlimBarWindow.qml missing"
# Must show RAM in the slim pill
grep -q 'RAM' "$app/SlimBarWindow.qml" || grep -q 'MemModule' "$app/SlimBarWindow.qml" || grep -q 'SlimMem' "$app/SlimBarWindow.qml" || fail "slim bar must show RAM usage"
# Must read the same sysinfo cache as the primary bar
grep -q 'sysinfo.json' "$app/SlimBarWindow.qml" || { [[ -f "$app/SlimMemModule.qml" ]] && grep -q 'sysinfo.json' "$app/SlimMemModule.qml"; } || fail "slim RAM must read the same sysinfo.json cache as primary"
# Must format identically to primary (memoryUsed helper)
grep -q 'memoryUsed' "$app/SlimBarWindow.qml" || { [[ -f "$app/SlimMemModule.qml" ]] && grep -q 'memoryUsed' "$app/SlimMemModule.qml"; } || fail "slim RAM must use memoryUsed formatting like primary"
# Display-only: must not open the system panel / must not host SystemPanel
grep -q 'SystemPanel' "$app/SlimBarWindow.qml" && fail "slim RAM must be display-only (no SystemPanel popup)"
# Must not spawn duplicate fetchers (center CpuModule owns hypr-sysinfo)
grep -q 'hypr-sysinfo' "$app/SlimBarWindow.qml" && fail "slim bar must not spawn hypr-sysinfo (reuse center cache)"
if [[ -f "$app/SlimMemModule.qml" ]]; then
  grep -q 'hypr-sysinfo' "$app/SlimMemModule.qml" && fail "SlimMemModule must not spawn hypr-sysinfo"
fi
printf 'PASS: slim RAM display wired\n'
