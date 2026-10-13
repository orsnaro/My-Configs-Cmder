#!/usr/bin/env bash
set -euo pipefail
# Reminder daemon contract: fires once per event/task, never twice.
script="$HOME/.config/gcal/gcal-remind.py"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

[[ -f "$script" ]] || fail "gcal-remind.py missing"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export GCAL_DIR="$tmp" DRYRUN=1
soon=$(date -u -d '+5 min' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+5M +%Y-%m-%dT%H:%M:%SZ)
today=$(date +%Y-%m-%d)
python3 -c "import json; json.dump({'updated':'x','events':[{'summary':'Soon Meeting','start':'$soon','end':'$soon','allDay':False}],'tasks':[{'title':'Pay bill','due':'$today','list':'My Tasks'}]}, open('$tmp/cache.json','w'))"
venv="$HOME/.config/gcal/.venv/bin/python"
out1=$($venv "$script"); out2=$($venv "$script")
echo "$out1" | grep -q "Soon Meeting" || fail "first run must fire the event"
echo "$out1" | grep -q "Pay bill" || fail "first run must fire the task"
[[ -z "$out2" ]] || fail "second run must be silent, got: $out2"
# Live cache smoke: must not crash on the real data.
GCAL_DIR="$HOME/.config/gcal" DRYRUN=1 $venv "$script" >/dev/null || fail "live cache smoke failed"
printf 'PASS: reminders fire once\n'
