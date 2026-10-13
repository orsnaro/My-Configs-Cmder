#!/usr/bin/env python3
"""Sync Google Calendar + Tasks into ~/.config/gcal/cache.json.

Read-only. Refreshes the OAuth token itself. The statusbar CalendarPanel
polls this script and renders the cache - no secrets leave this machine.
"""
import datetime
import json
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CONF_DIR = os.path.expanduser("~/.config/gcal")
TOKEN = os.path.join(CONF_DIR, "token.json")
CACHE = os.path.join(CONF_DIR, "cache.json")
DAYS = 14


def entry(summary, start, end, all_day):
    return {"summary": summary, "start": start, "end": end,
            "allDay": all_day}


def main() -> int:
    if not os.path.exists(TOKEN):
        print("no token; run gcal-consent.py first", file=sys.stderr)
        return 1
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    now = datetime.datetime.now(datetime.timezone.utc)
    time_min = now.isoformat()
    time_max = (now + datetime.timedelta(days=DAYS)).isoformat()

    cal = build("calendar", "v3", credentials=creds)
    events = []
    for cal_item in cal.calendarList().list().execute().get("items", []):
        cid = cal_item["id"]
        items = cal.events().list(
            calendarId=cid, timeMin=time_min, timeMax=time_max,
            singleEvents=True, orderBy="startTime",
            maxResults=50).execute().get("items", [])
        for e in items:
            if e.get("status") == "cancelled":
                continue
            s, en = e.get("start", {}), e.get("end", {})
            all_day = "date" in s
            events.append(entry(
                e.get("summary", "(no title)"),
                s.get("dateTime", s.get("date", "")),
                en.get("dateTime", en.get("date", "")),
                all_day))
    events.sort(key=lambda e: e["start"])

    tasks_api = build("tasks", "v1", credentials=creds)
    tasks = []
    for lst in tasks_api.tasklists().list().execute().get("items", []):
        items = tasks_api.tasks().list(
            tasklist=lst["id"], showCompleted=False,
            maxResults=50).execute().get("items", [])
        for t in items:
            if t.get("status") == "completed":
                continue
            tasks.append({"title": t.get("title", "(no title)"),
                          "due": t.get("due", ""),
                          "list": lst["title"]})

    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"updated": time_min, "events": events,
                   "tasks": tasks}, f)
    os.replace(tmp, CACHE)
    print("events=%d tasks=%d" % (len(events), len(tasks)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
