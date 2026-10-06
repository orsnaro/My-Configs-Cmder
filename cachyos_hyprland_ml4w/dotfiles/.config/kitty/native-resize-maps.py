#!/usr/bin/env python3
"""Emit native resize maps only when this Kitty build has the ORS patch.

Read by kitty.conf via `geninclude` at config load. stdout becomes config
lines; anything else (notifications, marker files) is a side effect.

- Patched kitty: prints four later `resize_divider` maps that take
  precedence over the script fallback maps in custom.conf.
- Stock kitty (or patch overwritten by an update): prints nothing, so the
  `absolute-resize.py` fallback maps stay active, and fires a one-time
  desktop alert per kitty source hash.

Probe is a text scan (milliseconds, stdlib only): importing kitty.tabs
here would cost ~0.2s per config load and can disagree with the running
process when stale __pycache__ exists. NOTE: after (re-)applying the
patch to /usr/lib/kitty, purge __pycache__ or new processes keep old code.
"""

import hashlib
import os
import subprocess

KITTY_LIB = '/usr/lib/kitty/kitty'
ALERT_SUMMARY = '⚠️ WARNING!: Kitty update removed ORS native pans resize code edits!'
ALERT_BODY = 'custom pan resize .py script fallback is active.'


def source_hash():
    try:
        with open(os.path.join(KITTY_LIB, 'tabs.py'), 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:12]
    except OSError:
        return 'unknown'


def probe_native():
    try:
        with open(os.path.join(KITTY_LIB, 'tabs.py')) as f:
            tabs = f.read()
        with open(os.path.join(KITTY_LIB, 'options', 'utils.py')) as f:
            utils = f.read()
    except OSError:
        return False
    return 'def resize_divider' in tabs and "func_with_args('resize_divider')" in utils


def cache_dir():
    d = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
    return d


def maybe_alert(src_hash):
    marker = os.path.join(cache_dir(), 'kitty-ors-native-alert-{}'.format(src_hash))
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return
    except OSError:
        return
    with os.fdopen(fd, 'w') as f:
        f.write('alerted\n')
    try:
        subprocess.run(
            ['notify-send', '--urgency=critical', '--expire-time=15000',
             '--app-name=kitty', ALERT_SUMMARY, ALERT_BODY],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
        )
    except Exception:
        pass


def main():
    if probe_native():
        for key, direction in (('j', 'left'), ('l', 'right'),
                               ('i', 'up'), ('k', 'down')):
            # Same fallback as custom.conf so native resize works in ara too.
            print('map --allow-fallback=shifted,ascii ctrl+alt+{} resize_divider {}'.format(key, direction))
    else:
        maybe_alert(source_hash())
    return 0


# NOTE: no `if __name__ == '__main__': sys.exit(...)` guard here on purpose.
# Kitty executes this file in-process via runpy with __name__ == '__main__',
# so raising SystemExit would propagate into Kitty's config loader and kill
# it. Plain main() call: emits the maps and returns normally.
main()
