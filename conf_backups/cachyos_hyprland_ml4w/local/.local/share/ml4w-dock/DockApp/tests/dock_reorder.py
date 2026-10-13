#!/usr/bin/env python3
"""Run real QtTest gestures in Quickshell with disposable settings and apps.

Requires an existing Wayland session, qs and Python; installs nothing. The
production QML is symlinked, not copied or instrumented. Artifacts are retained
under /tmp/opencode for inspection, including native config-save telemetry.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import select
import shutil
import struct
import subprocess
import tempfile
import threading


class SaveMonitor:
    """Count completed writes/atomic replacements of the real settings file."""

    def __init__(self, config: Path, output: Path) -> None:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.inotify_init1.argtypes = [ctypes.c_int]
        libc.inotify_init1.restype = ctypes.c_int
        libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        libc.inotify_add_watch.restype = ctypes.c_int
        self.fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0 or libc.inotify_add_watch(
            self.fd, os.fsencode(config.parent), 0x00000008 | 0x00000080
        ) < 0:
            raise OSError(ctypes.get_errno(), "cannot monitor isolated settings")
        self.config = config
        self.output = output
        self.count = 0
        self.stopped = threading.Event()
        self.output.write_text("0\n")
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self) -> None:
        while not self.stopped.is_set():
            if not select.select([self.fd], [], [], 0.1)[0]:
                continue
            data = os.read(self.fd, 65536)
            offset = 0
            while offset < len(data):
                _, mask, _, length = struct.unpack_from("iIII", data, offset)
                name = data[offset + 16 : offset + 16 + length].split(b"\0", 1)[0]
                offset += 16 + length
                if name == os.fsencode(self.config.name) and mask & (0x8 | 0x80):
                    self.count += 1
                    temporary = self.output.with_suffix(".new")
                    temporary.write_text(f"{self.count}\n")
                    temporary.replace(self.output)

    def close(self) -> None:
        self.stopped.set()
        self.thread.join()
        os.close(self.fd)


def main() -> int:
    qs = shutil.which("qs")
    if not qs or not os.environ.get("WAYLAND_DISPLAY"):
        print("BLOCKED: requires installed qs and an existing Wayland session")
        return 2
    tests = Path(__file__).resolve().parent
    root = Path(tempfile.mkdtemp(prefix="dock-reorder-", dir="/tmp/opencode"))
    home = root / "home"
    config = home / ".config/ml4w-dock/config.json"
    apps = home / ".local/share/applications"
    binaries = home / "bin"
    config.parent.mkdir(parents=True)
    apps.mkdir(parents=True)
    binaries.mkdir()
    (root / "DockApp").symlink_to(tests.parent)
    (root / "shell.qml").symlink_to(tests / "tst_dock_reorder.qml")
    icon = root / "fixture.svg"
    icon.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
                    '<rect width="32" height="32" fill="#4488cc"/></svg>')
    for letter in "abcd":
        launcher = binaries / f"dock-reorder-alias-{letter}"
        launcher.write_text("#!/bin/sh\n"
                            f"printf '%s\\n' 'dock-reorder-{letter}' >> \"$DOCK_REORDER_ACTIVATIONS\"\n")
        launcher.chmod(0o700)
        (apps / f"dock-reorder-{letter}.desktop").write_text(
            "[Desktop Entry]\nType=Application\n"
            f"Name=Reorder fixture {letter.upper()}\nExec={launcher}\nIcon={icon}\n"
            "Terminal=false\nStartupNotify=false\n"
        )
    colors = config.parent / "colors.json"
    colors.write_text("{}\n")
    fixture = {
        "dock": {"enabled": True, "autohide": False, "reserveSpace": False,
                 "launcherButton": True, "launcherCommand": str(binaries / "dock-reorder-alias-a"),
                 "iconSize": 32, "monitor": ""},
        "pill": {"animationDuration": 0},
        "border": {"width": 3},
        "theme": {"colorsFile": str(colors)},
        "apps": {"pinned": [f"dock-reorder-{letter}" for letter in "abcd"],
                 "fixture": "preserve app settings"},
        "unrelated": {"sentinel": "preserve unknown groups"},
    }
    fixture_path = root / "fixture.json"
    fixture_path.write_text(json.dumps(fixture) + "\n")
    config.write_text(fixture_path.read_text())
    activations = root / "activations.log"
    activations.touch()
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_DATA_HOME=str(home / ".local/share"), XDG_DATA_DIRS=str(home / ".local/share"),
               XDG_CACHE_HOME=str(home / ".cache"),
               DOCK_REORDER_ARTIFACTS=str(root), DOCK_REORDER_ACTIVATIONS=str(activations),
               QT_WAYLAND_APP_ID="dock-reorder-test-host")
    monitor = SaveMonitor(config, root / "writes.txt")
    failed = False
    try:
        for phase in ("gestures", "restart"):
            env["DOCK_REORDER_PHASE"] = phase
            log = root / f"{phase}.log"
            print(f"Running {phase}; artifacts: {root}", flush=True)
            try:
                with log.open("w") as output:
                    process = subprocess.run([qs, "-p", str(root), "--no-color"],
                                             env=env, stdout=output, stderr=subprocess.STDOUT,
                                             timeout=120, check=False)
            except subprocess.TimeoutExpired:
                print(f"BLOCKED: {phase} timed out; see {log}")
                return 2
            result_path = root / f"{phase}-result.json"
            if process.returncode or not result_path.exists():
                print(log.read_text())
                print(f"BLOCKED: {phase} did not finish QtTest (exit {process.returncode})")
                return 2
            result = json.loads(result_path.read_text())
            for line in log.read_text().splitlines():
                if "REORDER_ASSERT" in line or "REORDER_CASE" in line:
                    print(line)
            print(f"{phase}: {result['passed']} passed, {result['failed']} failed, "
                  f"{result['skipped']} skipped")
            if result["passed"] + result["failed"] < 2 or result["skipped"]:
                print("BLOCKED: no complete, unskipped behavioral run")
                return 2
            failed = failed or bool(result["failed"])
    finally:
        monitor.close()
    print(f"{'FAIL' if failed else 'PASS'}: real DockWindow/DockItem Qt mouse tests; {root}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
