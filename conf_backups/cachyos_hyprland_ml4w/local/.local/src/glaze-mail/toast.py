#!/usr/bin/env python3
"""Native aerc Inbox toast hook; no mail fetch or background worker."""
from __future__ import annotations

from collections.abc import Mapping
import html
import os
import subprocess
import sys


def _plain(value: str) -> str:
    return " ".join(value.replace("\x00", "").split())[:200]


def notification_args(environ: Mapping[str, str]) -> list[str] | None:
    if environ.get("AERC_ACCOUNT_BACKEND", "").lower() != "imap":
        return None
    if environ.get("AERC_FOLDER", "").upper() != "INBOX":
        return None
    sender = _plain(environ.get("AERC_FROM_NAME") or environ.get("AERC_FROM_ADDRESS") or "New mail")
    account = _plain(environ.get("AERC_ACCOUNT", "Mail"))
    subject = html.escape(_plain(environ.get("AERC_SUBJECT") or "No subject"))
    return ["notify-send", "-a", "Mail", "-i", "mail-message-new", "--", f"{sender} ({account})", subject]


def main() -> int:
    args = notification_args(os.environ)
    if args is None:
        return 0
    try:
        subprocess.run(args, shell=False, check=True, timeout=5, capture_output=True)
        return 0
    except (OSError, subprocess.SubprocessError):
        print("Mail toast could not be delivered to the desktop notification service.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
