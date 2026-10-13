#!/usr/bin/env python3
"""Fire desktop notifications (+sound) for imminent events and due tasks.

Reads cache.json (gcal-sync.py), keeps fired markers in notified.json so each
item fires once. Env: GCAL_DIR overrides ~/.config/gcal (tests), DRYRUN=1
prints instead of notifying.
"""
import datetime
import json
import os
import subprocess
import sys

CONF_DIR = os.environ.get("GCAL_DIR", os.path.expanduser("~/.config/gcal"))
CACHE = os.path.join(CONF_DIR, "cache.json")
STATE = os.path.join(CONF_DIR, "notified.json")
DRYRUN = os.environ.get("DRYRUN") == "1"
EVENT_WINDOW_MIN = 15
SOUND = "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def parse_dt(s):
    try:
        d = datetime.datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        return d
    except (ValueError, TypeError):
        return None


def notify(title, body):
    if DRYRUN:
        print("NOTIFY: %s -- %s" % (title, body))
        return
    subprocess.run(["notify-send", "--app-name=Calendar", title, body],
                   check=False)
    if os.path.exists(SOUND):
        subprocess.run(["paplay", SOUND], check=False)


def main() -> int:
    cache = load(CACHE, None)
    if cache is None:
        return 0
    state = load(STATE, {})
    today = datetime.date.today().isoformat()
    state = {k: v for k, v in state.items() if v.get("day") == today}
    now = datetime.datetime.now(datetime.timezone.utc)
    changed = False

    for e in cache.get("events", []):
        key = "e:" + e.get("start", "") + e.get("summary", "")
        if key in state:
            continue
        start = parse_dt(e.get("start", ""))
        if start is None:
            continue
        delta = (start - now).total_seconds() / 60
        if 0 <= delta <= EVENT_WINDOW_MIN:
            when = "now" if delta < 1 else "in %d min" % int(delta)
            notify("Upcoming: %s (%s)" % (e.get("summary", "(no title)"),
                                          when),
                   e.get("start", ""))
            state[key] = {"day": today}
            changed = True

    for t in cache.get("tasks", []):
        due = (t.get("due") or "")[:10]
        if not due or due > today:
            continue
        key = "t:" + due + t.get("title", "")
        if key in state:
            continue
        notify("Due today: " + t.get("title", "(no title)"), t.get("list", ""))
        state[key] = {"day": today}
        changed = True

    if changed or not os.path.exists(STATE):
        save(STATE, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
