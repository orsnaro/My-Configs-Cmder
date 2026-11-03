#!/usr/bin/env python3
"""List central Gmail folders and capabilities without fetching messages."""
from __future__ import annotations

from contextlib import suppress
from typing import Any
import imaplib
import json
import ssl
import sys

from oauth import EXPECTED_EMAIL, STATE_DIRECTORY, access_token


def inspect_mailbox(access_token: str, email: str) -> dict[str, Any]:
    if email != EXPECTED_EMAIL or not access_token or any(c in access_token for c in "\r\n\x00\x01"):
        raise ValueError("Invalid central-mailbox credential")
    client = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=ssl.create_default_context(), timeout=30)
    responded = False

    def authenticate(challenge: bytes) -> bytes:
        nonlocal responded
        if responded:
            return b""
        responded = True
        return f"user={email}\x01auth=Bearer {access_token}\x01\x01".encode()

    try:
        status, _ = client.authenticate("XOAUTH2", authenticate)
        if status != "OK":
            raise ValueError("Mail authentication failed")
        status, capabilities = client.capability()
        if status != "OK":
            raise ValueError("Cannot inspect server capabilities")
        status, folders = client.list()
        if status != "OK":
            raise ValueError("Cannot list server folders")
        status, count = client.select("INBOX", readonly=True)
        if status != "OK":
            raise ValueError("Cannot examine the central Inbox")
        return {
            "account": email,
            "capabilities": b" ".join(x for x in capabilities if x is not None).decode("ascii", errors="replace").split(),
            "folders_raw": [x.decode("utf-8", errors="replace") for x in folders if x is not None],
            "inbox_messages": int(count[0]),
            "read_only": True,
            "message_bodies_fetched": 0,
        }
    finally:
        with suppress(imaplib.IMAP4.error, OSError):
            client.logout()


def main() -> int:
    try:
        result = inspect_mailbox(access_token(STATE_DIRECTORY), EXPECTED_EMAIL)
        print(json.dumps(result, indent=2))
        return 0
    except Exception:
        print("Read-only Gmail probe failed; no message contents or credential values were logged.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
