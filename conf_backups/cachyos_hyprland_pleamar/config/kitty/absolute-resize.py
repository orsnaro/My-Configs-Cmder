#!/usr/bin/env python3
"""Absolute (WT-style) pane resize for kitty, one divider step per keypress.

WT semantics: the key names the direction the DIVIDER moves, regardless of
which pane has focus. Kitty's built-in resize actions are focus-relative,
so this script uses the split tree from `kitty @ ls` to determine which
side of the nearest divider the active pane occupies, then resizes it in place.
Focus never moves, so there is nothing to restore.

Needs no `allow_remote_control` in kitty.conf: it is launched via the
`remote_control_script` map action, which grants this process alone a
dedicated control socket (KITTY_LISTEN_ON=fd:N, passed through to the
`kitty @` grandchildren explicitly since Python closes fds by default).

In nested splits Kitty resizes the pane's nearest matching split on the
requested axis; a pane with dividers on both sides can only move that one.
"""
import json
import os
import shutil
import subprocess
import sys

STEP_CELLS = 6
# Reuse the working executable for both calls in this script invocation.
# Each keypress starts a new process, so this is not a cross-keypress cache.
# Default to the stock path; corrected on the fly if it cannot start.
_kitty_exe = "/usr/bin/kitty"


def run_kitty_with_fallback(args, env, pass_fds):
    """Run one `kitty @` command, trying known executable locations in order.

    Retries only when an executable cannot start. A `kitty @` error is
    returned as-is so a resize is never applied twice.
    """
    global _kitty_exe
    fixed = [exe for exe in (
        _kitty_exe,
        "/usr/bin/kitty",
        "/usr/local/bin/kitty",
        os.path.expanduser("~/.local/bin/kitty"),
    ) if exe]
    tried = set()
    last_error = None
    for exe in fixed + [None]:  # trailing None means "search PATH now"
        if exe is None:
            exe = shutil.which("kitty")
            if not exe:
                break
        if exe in tried:
            continue
        tried.add(exe)
        try:
            result = subprocess.run(
                [exe, "@"] + list(args),
                env=env,
                capture_output=True,
                text=True,
                pass_fds=pass_fds,
                timeout=15,
            )
        except OSError as error:
            last_error = error
            continue
        _kitty_exe = exe
        return result
    if last_error:
        raise last_error
    raise FileNotFoundError("No kitty executable could be started")


def kitty_cmd(*args):
    env = dict(os.environ)
    pass_fds = []
    listen = env.get("KITTY_LISTEN_ON", "")
    if listen.startswith("fd:"):
        try:
            pass_fds = [int(listen[3:])]
        except ValueError:
            pass
    return run_kitty_with_fallback(list(args), env, pass_fds)


def find_active_window():
    out = kitty_cmd("ls", "--match=state:focused")
    if out.returncode != 0:
        return None
    try:
        data = json.loads(out.stdout)
    except ValueError:
        return None
    for osw in data:
        for tab in osw.get("tabs", []):
            for w in tab.get("windows", []):
                if w.get("is_focused"):
                    return w, tab
    return None


def nearest_split_side(tab, window_id, horizontal):
    """Return which side of the nearest same-axis split owns the window."""
    group_id = next((g.get("id") for g in tab.get("groups", ()) if window_id in g.get("windows", ())), None)
    if group_id is None:
        return None

    def search(node):
        if isinstance(node, int):
            return node == group_id, None
        if not isinstance(node, dict):
            return False, None
        for side in ("one", "two"):
            contains, nearest = search(node.get(side))
            if contains:
                if nearest is not None:
                    return True, nearest
                if node.get("horizontal", True) == horizontal and node.get("one") is not None and node.get("two") is not None:
                    return True, side
                return True, None
        return False, None

    return search(tab.get("layout_state", {}).get("pairs"))[1]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("left", "right", "up", "down"):
        return 0
    direction = sys.argv[1]
    try:
        found = find_active_window()
        if found is None:
            return 0
        active, tab = found
        if "id" not in active:
            return 0
        neighbors = active.get("neighbors", {}) or {}
        if direction == "left":
            axis, inc = "horizontal", STEP_CELLS if neighbors.get("left") else -STEP_CELLS
        elif direction == "right":
            axis, inc = "horizontal", STEP_CELLS if neighbors.get("right") else -STEP_CELLS
        elif direction == "up":
            axis, inc = "vertical", STEP_CELLS if neighbors.get("top") else -STEP_CELLS
        else:  # down
            axis, inc = "vertical", STEP_CELLS if neighbors.get("bottom") else -STEP_CELLS
        if tab.get("layout") == "splits":
            side = nearest_split_side(tab, active["id"], axis == "horizontal")
            if side is None:
                return 0
            toward_first = direction in ("left", "up")
            inc = STEP_CELLS if (side == "two") == toward_first else -STEP_CELLS
        kitty_cmd(
            "resize-window",
            "--match=id:{}".format(active["id"]),
            "--axis={}".format(axis),
            "--increment={}".format(inc),
        )
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
