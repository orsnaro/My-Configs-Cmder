#!/usr/bin/env bash
set -euo pipefail
# Calendar agenda contract: panel renders Google events + tasks from the
# sync cache, refreshed on open and periodically.
panel="$HOME/.config/quickshell/StatusbarApp/CalendarPanel.qml"
cache="$HOME/.config/gcal/cache.json"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -f "$cache" ]] || fail "gcal cache.json missing (run gcal-sync.py)"
python3 -c "import json;d=json.load(open('$cache'));assert 'events' in d and 'tasks' in d" \
    || fail "cache must carry events and tasks arrays"
need "$panel" "gcal/cache.json" "CalendarPanel must read the gcal cache"
need "$panel" "agendaEvents" "CalendarPanel must parse agenda events"
need "$panel" "agendaTasks" "CalendarPanel must parse agenda tasks"
need "$panel" "gcal-sync" "CalendarPanel must trigger a sync"
printf 'PASS: calendar agenda wired\n'
