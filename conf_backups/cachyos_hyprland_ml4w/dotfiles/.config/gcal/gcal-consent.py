#!/usr/bin/env python3
"""One-time Google OAuth consent: mints ~/.config/gcal/token.json.

Scopes: read-only Calendar + Tasks. Run once; the sync job refreshes the
token itself afterwards. Prints the consent URL - open it in Brave on this
machine so the localhost redirect reaches this script.
"""
import glob
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]
CONF_DIR = os.path.expanduser("~/.config/gcal")
TOKEN = os.path.join(CONF_DIR, "token.json")


def main() -> int:
    secrets = sorted(glob.glob("/shared_across_des/client_secret_*.json"))
    if not secrets:
        print("no client_secret_*.json in /shared_across_des", file=sys.stderr)
        return 1
    os.makedirs(CONF_DIR, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(secrets[0], SCOPES)
    # The server prints its own URL (with the matching redirect) to stdout;
    # relay that exact URL to the browser.
    flow.run_local_server(port=8080, open_browser=False,
                          authorization_prompt_message="OPEN_IN_BRAVE:{url}")
    with open(TOKEN, "w") as f:
        f.write(flow.credentials.to_json())
    os.chmod(TOKEN, 0o600)
    print("saved " + TOKEN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
