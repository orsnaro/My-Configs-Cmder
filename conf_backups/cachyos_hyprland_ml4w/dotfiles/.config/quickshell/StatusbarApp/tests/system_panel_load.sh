#!/usr/bin/env bash
set -euo pipefail
# Live integration check: the real Quickshell instance must have loaded the
# panel without the QML property error that previously hid the entire bar.
id=$(qs list | sed -n 's/^Instance \([^:]*\):/\1/p' | head -1)
[[ -n "$id" ]] || { echo 'SKIP: Quickshell is not running'; exit 0; }
log="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/quickshell/by-id/$id/log.qslog"
[[ -f "$log" ]] || { echo "FAIL: missing live log $log" >&2; exit 1; }
fresh=$(python3 - "$log" <<'PY'
import sys
content = open(sys.argv[1], 'rb').read()
index = content.rfind(b'Reloading configuration')
if index < 0:
    raise SystemExit('FAIL: no reload found in live Quickshell log')
print(content[index:].decode('utf-8', errors='replace').replace('\0', ''))
PY
)
grep -q 'Configuration Loaded' <<<"$fresh" || { echo 'FAIL: latest reload did not finish' >&2; exit 1; }
if grep -Eq 'SystemPanel unavailable|SystemPanelState unavailable|Cannot assign to non-existent property "modB"|sysPanel is not defined|cancelHides is not a function' <<<"$fresh"; then
    echo 'FAIL: system metrics panel did not load' >&2
    grep -E 'SystemPanel unavailable|Cannot assign to non-existent property|sysPanel is not defined|cancelHides is not a function' <<<"$fresh" | head -5 >&2
    exit 1
fi
echo 'PASS: system metrics panel loads in Quickshell'
