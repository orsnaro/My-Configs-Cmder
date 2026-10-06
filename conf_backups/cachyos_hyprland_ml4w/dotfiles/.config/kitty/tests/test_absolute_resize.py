"""Resize-script unit tests and live two-pane regression test.

Run in a scratch Kitty with a control socket and exactly two stacked panes:
KITTY_TEST_PID=<window-pid> KITTY_TEST_TO=unix:/path/to/socket python3 -m unittest discover -s ~/.config/kitty/tests
The scratch Kitty must be the currently focused OS window.
"""

import importlib.util
import json
import os
import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "absolute-resize.py"
spec = importlib.util.spec_from_file_location("absolute_resize", SCRIPT)
resize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resize)


class ResizeScriptTest(unittest.TestCase):
    def setUp(self):
        resize._kitty_exe = None

    def test_queries_only_focused_window_and_preserves_neighbors(self):
        response = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([{"tabs": [{"windows": [{
                "id": 42, "is_focused": True, "neighbors": {"right": [43]},
            }]}]}]), stderr="",
        )
        with patch.object(resize.subprocess, "run", return_value=response) as run:
            window, tab = resize.find_active_window()

        self.assertEqual(window["neighbors"], {"right": [43]})
        self.assertEqual(tab["windows"], [window])
        self.assertEqual(run.call_args.args[0][1:], ["@", "ls", "--match=state:focused"])

    def test_tries_other_fixed_path_when_stock_executable_cannot_start(self):
        attempted = []

        def run(command, **kwargs):
            attempted.append(command[0])
            if command[0] == "/usr/bin/kitty":
                raise FileNotFoundError(command[0])
            return subprocess.CompletedProcess(command, 0, "[]", "")

        with patch.object(resize.subprocess, "run", side_effect=run), \
                patch.object(resize.shutil, "which", side_effect=AssertionError("PATH search was unnecessary")):
            result = resize.kitty_cmd("ls")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(attempted, ["/usr/bin/kitty", "/usr/local/bin/kitty"])

    def test_searches_path_only_after_fixed_paths_cannot_start(self):
        attempted = []

        def run(command, **kwargs):
            attempted.append(command[0])
            if command[0] != "/opt/kitty/bin/kitty":
                raise FileNotFoundError(command[0])
            return subprocess.CompletedProcess(command, 0, "[]", "")

        with patch.object(resize.subprocess, "run", side_effect=run), \
                patch.object(resize.shutil, "which", return_value="/opt/kitty/bin/kitty") as which:
            result = resize.kitty_cmd("ls")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(attempted, [
            "/usr/bin/kitty", "/usr/local/bin/kitty",
            str(Path.home() / ".local/bin/kitty"), "/opt/kitty/bin/kitty",
        ])
        which.assert_called_once_with("kitty")

    def test_reuses_working_executable_for_both_remote_calls(self):
        attempted = []

        def run(command, **kwargs):
            attempted.append(command[0])
            if command[0] == "/usr/bin/kitty":
                raise FileNotFoundError(command[0])
            return subprocess.CompletedProcess(command, 0, "[]", "")

        with patch.object(resize.subprocess, "run", side_effect=run), \
                patch.object(resize.shutil, "which", side_effect=AssertionError("PATH search was unnecessary")):
            resize.kitty_cmd("ls")
            resize.kitty_cmd("resize-window", "--match=id:42")

        self.assertEqual(attempted, [
            "/usr/bin/kitty", "/usr/local/bin/kitty", "/usr/local/bin/kitty",
        ])

    def test_does_not_retry_a_kitty_command_that_returns_an_error(self):
        response = subprocess.CompletedProcess(["/usr/bin/kitty", "@", "ls"], 1, "", "socket error")
        with patch.object(resize.subprocess, "run", return_value=response) as run, \
                patch.object(resize.shutil, "which", side_effect=AssertionError("PATH search was unnecessary")):
            result = resize.kitty_cmd("ls")

        self.assertIs(result, response)
        self.assertEqual(run.call_count, 1)

    def test_right_shrinks_middle_pane_from_left_in_left_nested_split(self):
        tab = {
            "layout": "splits",
            "layout_state": {"pairs": {"one": {"one": 4, "two": 6}, "two": 5}},
            "groups": [{"id": 4, "windows": [4]}, {"id": 6, "windows": [6]}, {"id": 5, "windows": [5]}],
            "windows": [{"id": 6, "is_focused": True, "neighbors": {"left": [4], "right": [5]}}],
        }
        listing = subprocess.CompletedProcess([], 0, json.dumps([{"tabs": [tab]}]), "")
        calls = []

        def kitty(*args):
            calls.append(args)
            return listing

        with patch.object(resize, "kitty_cmd", side_effect=kitty), \
                patch.object(resize.sys, "argv", [str(SCRIPT), "right"]):
            resize.main()

        self.assertEqual(calls[-1], (
            "resize-window", "--match=id:6", "--axis=horizontal", "--increment=-6",
        ))

    def test_left_shrinks_middle_pane_from_right_in_five_pane_layout(self):
        tab = {
            "layout": "splits",
            "layout_state": {"pairs": {
                "horizontal": False,
                "one": {"one": 7, "two": {"one": 9, "two": 10}},
                "two": {"one": 8, "two": 11},
            }},
            "groups": [{"id": n, "windows": [n]} for n in (7, 8, 9, 10, 11)],
            "windows": [{"id": 9, "is_focused": True,
                         "neighbors": {"left": [7], "right": [10], "bottom": [11]}}],
        }
        listing = subprocess.CompletedProcess([], 0, json.dumps([{"tabs": [tab]}]), "")
        calls = []

        def kitty(*args):
            calls.append(args)
            return listing

        with patch.object(resize, "kitty_cmd", side_effect=kitty), \
                patch.object(resize.sys, "argv", [str(SCRIPT), "left"]):
            resize.main()

        self.assertEqual(calls[-1], (
            "resize-window", "--match=id:9", "--axis=horizontal", "--increment=-6",
        ))

    def test_down_shrinks_middle_pane_in_vertically_nested_split(self):
        tab = {
            "layout": "splits",
            "layout_state": {"pairs": {"horizontal": False,
                                       "one": {"horizontal": False, "one": 40, "two": 60}, "two": 50}},
            "groups": [{"id": 40, "windows": [4]}, {"id": 60, "windows": [6]},
                       {"id": 50, "windows": [5]}],
            "windows": [{"id": 6, "is_focused": True, "neighbors": {"top": [4], "bottom": [5]}}],
        }
        listing = subprocess.CompletedProcess([], 0, json.dumps([{"tabs": [tab]}]), "")
        calls = []

        def kitty(*args):
            calls.append(args)
            return listing

        with patch.object(resize, "kitty_cmd", side_effect=kitty), \
                patch.object(resize.sys, "argv", [str(SCRIPT), "down"]):
            resize.main()

        self.assertEqual(calls[-1], (
            "resize-window", "--match=id:6", "--axis=vertical", "--increment=-6",
        ))

    def test_does_not_guess_divider_when_split_tree_is_missing(self):
        tab = {
            "layout": "splits",
            "layout_state": {},
            "groups": [],
            "windows": [{"id": 6, "is_focused": True, "neighbors": {"left": [4], "right": [5]}}],
        }
        listing = subprocess.CompletedProcess([], 0, json.dumps([{"tabs": [tab]}]), "")
        calls = []

        def kitty(*args):
            calls.append(args)
            return listing

        with patch.object(resize, "kitty_cmd", side_effect=kitty), \
                patch.object(resize.sys, "argv", [str(SCRIPT), "right"]):
            resize.main()

        self.assertEqual(calls, [("ls", "--match=state:focused")])


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


@unittest.skipUnless(os.getenv("KITTY_TEST_PID") and os.getenv("KITTY_TEST_TO"), "requires a focused scratch Kitty")
class AbsoluteResizeTest(unittest.TestCase):
    def test_down_moves_divider_down_from_top_without_losing_focus(self):
        pid = int(os.environ["KITTY_TEST_PID"])
        socket = os.environ["KITTY_TEST_TO"]
        self.assertEqual(json.loads(run("hyprctl", "activewindow", "-j"))["pid"], pid)

        def windows():
            data = json.loads(run("kitty", "@", "--to", socket, "ls"))
            tab = next(tab for tab in data[0]["tabs"] if tab["is_focused"])
            return tab["windows"]

        top = windows()[0]
        run("kitty", "@", "--to", socket, "resize-window", "--match=id:{}".format(top["id"]), "--axis=reset")
        run("wtype", "-M", "alt", "-k", "i", "-m", "alt")
        top, bottom = windows()
        self.assertTrue(top["is_focused"])
        self.assertEqual(top["neighbors"], {"bottom": [bottom["id"]]})
        before = top["lines"]

        run("wtype", "-M", "ctrl", "-M", "alt", "-k", "k", "-m", "alt", "-m", "ctrl")
        time.sleep(0.6)  # remote_control_script dispatch is asynchronous
        top, _ = windows()
        self.assertGreater(top["lines"], before, "Down should grow top pane and move divider down")
        self.assertTrue(top["is_focused"], "Resize must leave the original pane focused")


if __name__ == "__main__":
    unittest.main()
