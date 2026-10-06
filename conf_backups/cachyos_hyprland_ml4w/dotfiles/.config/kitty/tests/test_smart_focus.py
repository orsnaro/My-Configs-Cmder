"""No-UI focus tests; all compositor, socket and focus operations are isolated.

Run: python3 -m unittest discover -s ~/.config/kitty/tests -p 'test_smart_focus.py' -v
Loader smoke: kitty +runpy "import runpy; runpy.run_path('/home/narol/.config/kitty/tests/test_smart_focus.py')['run_loader_smoke']()"
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import sys
import unittest
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import Mock, call, patch


SCRIPT = Path(__file__).resolve().parents[1] / "smart-focus.py"
CONFIG = SCRIPT.with_name("custom.conf")
DIRECTIONS = (("left", "left"), ("right", "right"), ("up", "top"), ("down", "bottom"))


def load_script() -> ModuleType:
    """Stub only Kitty imports unavailable outside its embedded Python."""
    modules = {name: ModuleType(name) for name in (
        "kitty", "kitty.fast_data_types", "kittens", "kittens.tui", "kittens.tui.handler",
    )}
    modules["kitty"].__path__ = []
    modules["kittens"].__path__ = []
    modules["kittens.tui"].__path__ = []

    def result_handler(*, no_ui: bool = False) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorate(handler: Callable[..., Any]) -> Callable[..., Any]:
            setattr(handler, "no_ui", no_ui)
            return handler
        return decorate

    modules["kittens.tui.handler"].result_handler = result_handler
    modules["kitty.fast_data_types"].current_focused_os_window_id = Mock(return_value=11)
    spec = importlib.util.spec_from_file_location("smart_focus", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


def fake_boss(neighbor: int | None = None) -> SimpleNamespace:
    window = SimpleNamespace(id=7)
    return SimpleNamespace(
        active_window=window,
        active_tab=SimpleNamespace(
            os_window_id=11,
            active_window=window,
            neighboring_group_id=Mock(return_value=neighbor),
            windows=SimpleNamespace(set_active_group=Mock()),
            new_special_window=Mock(side_effect=AssertionError("no kitten overlay")),
        ),
        show_error=Mock(side_effect=AssertionError("no error overlay")),
    )


def source(class_name: str = "kitty", address: str = "0xAa07") -> dict[str, Any]:
    return {"pid": os.getpid(), "class": class_name, "address": address}


def expected_eval(direction: str, address: str = "0xAa07") -> str:
    return f'/eval checked_focus("{direction}", {os.getpid()}, "{address}")'


def forbid_processes(stack: ExitStack) -> None:
    for name in ("subprocess.run", "subprocess.Popen", "os.fork", "time.sleep"):
        stack.enter_context(patch(name, side_effect=AssertionError("no processes, waits or sleeps")))


class SmartFocusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.smart = load_script()
        self.assertTrue(callable(getattr(self.smart, "hypr_request", None)),
                        "edge routing requires the bounded direct IPC transport")
        self.boss = fake_boss()
        self.tab = self.boss.active_tab
        stack = ExitStack()
        self.addCleanup(stack.close)
        forbid_processes(stack)
        stack.enter_context(patch("socket.socket", side_effect=AssertionError("transport seam only")))

        def transport(request: str) -> str:
            if request == "j/activewindow":
                return json.dumps(source())
            return "ok"

        self.transport = stack.enter_context(patch.object(self.smart, "hypr_request", side_effect=transport))

    def invoke(self, args: list[str], target: int = 7) -> None:
        self.assertIsNone(self.smart.handle_result(args, None, target, self.boss))

    def assert_no_actions(self) -> None:
        self.tab.neighboring_group_id.assert_not_called()
        self.tab.windows.set_active_group.assert_not_called()
        self.transport.assert_not_called()

    def test_all_four_native_neighbors_activate_once_with_zero_ipc(self) -> None:
        for direction, edge in DIRECTIONS:
            with self.subTest(direction=direction):
                self.boss = fake_boss(neighbor=19)
                self.tab = self.boss.active_tab
                self.invoke(["smart-focus.py", direction])
                self.tab.neighboring_group_id.assert_called_once_with(edge)
                self.tab.windows.set_active_group.assert_called_once_with(19)
                self.transport.assert_not_called()

    def test_neighbor_is_checked_against_none_not_truthiness(self) -> None:
        self.tab.neighboring_group_id.return_value = 0
        self.invoke(["smart-focus.py", "left"])
        self.tab.neighboring_group_id.assert_called_once_with("left")
        self.tab.windows.set_active_group.assert_called_once_with(0)
        self.transport.assert_not_called()

    def test_all_four_edges_use_exactly_two_pid_and_address_guarded_requests(self) -> None:
        for direction, edge in DIRECTIONS:
            with self.subTest(direction=direction):
                self.transport.reset_mock()
                self.boss = fake_boss()
                self.tab = self.boss.active_tab
                self.invoke(["smart-focus.py", direction])
                self.tab.neighboring_group_id.assert_called_once_with(edge)
                self.tab.windows.set_active_group.assert_not_called()
                self.assertEqual(self.transport.call_args_list,
                                 [call("j/activewindow"), call(expected_eval(direction))])

    def test_no_ui_metadata_and_handler_does_not_call_main(self) -> None:
        self.assertTrue(getattr(self.smart.handle_result, "no_ui", False))
        with patch.object(self.smart, "main", side_effect=AssertionError("main must not run")):
            self.invoke(["smart-focus.py", "right"])
        self.assertEqual(self.transport.call_args_list,
                         [call("j/activewindow"), call(expected_eval("right"))])

    def test_main_is_loader_compatible_noop(self) -> None:
        self.assertIsNone(self.smart.main(["smart-focus.py", "left"]))
        self.assert_no_actions()

    def test_invalid_missing_and_multiple_direction_args_do_nothing(self) -> None:
        for args in ([], ["smart-focus.py"], ["smart-focus.py", "bogus"],
                     ["smart-focus.py", "left", "right"], ["left"],
                     ["smart-focus.py", 'left"); dangerous()'], ["smart-focus.py", "top"]):
            with self.subTest(args=args):
                self.invoke(args)
                self.assert_no_actions()
        self.smart.current_focused_os_window_id.assert_not_called()

    def test_no_active_tab_does_nothing(self) -> None:
        self.boss.active_tab = None
        self.invoke(["smart-focus.py", "left"])
        self.assert_no_actions()

    def test_no_active_window_does_nothing(self) -> None:
        self.boss.active_window = None
        self.tab.active_window = None
        self.invoke(["smart-focus.py", "left"])
        self.assert_no_actions()

    def test_stale_target_pane_does_nothing(self) -> None:
        for target in (0, 6, 19):
            with self.subTest(target=target):
                self.invoke(["smart-focus.py", "left"], target)
                self.assert_no_actions()

    def test_native_os_focus_mismatch_does_nothing(self) -> None:
        for os_window_id in (0, 12):
            with self.subTest(os_window_id=os_window_id):
                self.smart.current_focused_os_window_id.return_value = os_window_id
                self.invoke(["smart-focus.py", "left"])
                self.assert_no_actions()

    def test_repeated_genuine_calls_are_not_filtered(self) -> None:
        self.invoke(["smart-focus.py", "up"])
        self.invoke(["smart-focus.py", "up"])
        self.assertEqual(self.tab.neighboring_group_id.call_args_list, [call("top"), call("top")])
        self.assertEqual(self.transport.call_args_list, [
            call("j/activewindow"), call(expected_eval("up")),
            call("j/activewindow"), call(expected_eval("up")),
        ])
        self.tab.windows.set_active_group.assert_not_called()

    def test_ordered_two_edges_finish_each_eval_before_using_next_active_kitty_source(self) -> None:
        addresses = ("0xa1", "0xa2")
        current = 0

        def compositor(request: str) -> str:
            nonlocal current
            if request == "j/activewindow":
                return json.dumps(source(address=addresses[current]))
            self.assertEqual(request, expected_eval("left", addresses[current]))
            current += 1
            # The next physical callback comes from its own newly active OS window/pane.
            self.tab.os_window_id += 1
            self.boss.active_window = self.tab.active_window = SimpleNamespace(id=7 + current)
            self.smart.current_focused_os_window_id.return_value = self.tab.os_window_id
            return "ok"

        self.transport.side_effect = compositor
        self.invoke(["smart-focus.py", "left"], target=7)
        self.assertEqual(current, 1, "first edge must complete, not enqueue background work")
        self.invoke(["smart-focus.py", "left"], target=8)
        self.assertEqual(current, 2, "second edge must use its own active Kitty source")
        self.assertEqual(self.transport.call_args_list, [
            call("j/activewindow"), call(expected_eval("left", "0xa1")),
            call("j/activewindow"), call(expected_eval("left", "0xa2")),
        ])
        self.tab.windows.set_active_group.assert_not_called()

    def test_edge_query_failure_is_silent_without_activation(self) -> None:
        self.transport.side_effect = None
        self.transport.return_value = None
        self.invoke(["smart-focus.py", "down"])
        self.transport.assert_called_once_with("j/activewindow")
        self.tab.windows.set_active_group.assert_not_called()
        self.boss.show_error.assert_not_called()


class FocusDesktopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.smart = load_script()
        self.assertTrue(callable(getattr(self.smart, "focus_desktop", None)),
                        "edge routing requires synchronous validated focus_desktop")
        stack = ExitStack()
        self.addCleanup(stack.close)
        forbid_processes(stack)
        stack.enter_context(patch("socket.socket", side_effect=AssertionError("transport seam only")))
        self.transport = stack.enter_context(patch.object(self.smart, "hypr_request"))

    def test_valid_kitty_and_quake_sources_use_exact_pid_address_and_direction(self) -> None:
        for class_name in ("kitty", "quake-kitty"):
            for direction, _ in DIRECTIONS:
                with self.subTest(class_name=class_name, direction=direction):
                    self.transport.reset_mock()
                    self.transport.side_effect = [json.dumps(source(class_name)), "ok"]
                    self.assertIsNone(self.smart.focus_desktop(direction))
                    self.assertEqual(self.transport.call_args_list,
                                     [call("j/activewindow"), call(expected_eval(direction))])

    def test_missing_malformed_and_non_dict_json_never_evaluates(self) -> None:
        for response in (None, "", "not JSON", "[]", "null", "true", "123", '"kitty"', "{}"):
            with self.subTest(response=response):
                self.transport.reset_mock()
                self.transport.return_value = response
                self.assertIsNone(self.smart.focus_desktop("left"))
                self.transport.assert_called_once_with("j/activewindow")

    def test_wrong_missing_pid_or_non_kitty_class_never_evaluates(self) -> None:
        for field, value in (("pid", os.getpid() + 1), ("pid", None), ("pid", str(os.getpid())),
                             ("class", "brave-browser"), ("class", "Kitty"), ("class", None)):
            with self.subTest(field=field, value=value):
                invalid = source()
                invalid[field] = value
                self.transport.reset_mock()
                self.transport.return_value = json.dumps(invalid)
                self.smart.focus_desktop("left")
                self.transport.assert_called_once_with("j/activewindow")

    def test_missing_invalid_or_injection_like_address_never_evaluates(self) -> None:
        invalid_sources = [source()]
        del invalid_sources[0]["address"]
        for address in (None, 123, "", "0x", "abc", "0xzz", '0xabc"); dangerous()',
                        "\n0xabc", "0xabc\n", "0xabc extra"):
            invalid = source()
            invalid["address"] = address
            invalid_sources.append(invalid)
        for invalid in invalid_sources:
            with self.subTest(source=invalid):
                self.transport.reset_mock()
                self.transport.return_value = json.dumps(invalid)
                self.smart.focus_desktop("left")
                self.transport.assert_called_once_with("j/activewindow")

    def test_direct_invalid_direction_never_queries_or_evaluates(self) -> None:
        for direction in ("", "top", "diagonal", 'left"); dangerous()'):
            with self.subTest(direction=direction):
                self.assertIsNone(self.smart.focus_desktop(direction))
                self.transport.assert_not_called()

    def test_lost_eval_reply_is_not_retried(self) -> None:
        self.transport.side_effect = [json.dumps(source()), None]
        self.assertIsNone(self.smart.focus_desktop("right"))
        self.assertEqual(self.transport.call_args_list,
                         [call("j/activewindow"), call(expected_eval("right"))])


class RecordingSocket:
    """Context-managed transport double; no real socket or thread."""
    def __init__(self) -> None:
        self.connect = Mock()
        self.sendall = Mock()
        self.recv = Mock(side_effect=[b"ok", b""])
        self.settimeout = Mock()
        self.close = Mock()

    def __enter__(self) -> RecordingSocket:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


class HyprRequestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.smart = load_script()
        self.assertTrue(callable(getattr(self.smart, "hypr_request", None)),
                        "hypr_request must provide bounded local IPC")
        self.connection = RecordingSocket()
        stack = ExitStack()
        self.addCleanup(stack.close)
        forbid_processes(stack)
        stack.enter_context(patch.dict(os.environ, {
            "XDG_RUNTIME_DIR": "/isolated/runtime", "HYPRLAND_INSTANCE_SIGNATURE": "instance-test",
        }, clear=True))
        self.factory = stack.enter_context(patch("socket.socket", return_value=self.connection))
        self.clock = stack.enter_context(patch("time.monotonic", return_value=100.0))

    def assert_closed(self) -> None:
        self.connection.close.assert_called_once_with()

    def test_complete_response_uses_local_path_and_closes_socket(self) -> None:
        self.assertEqual(self.smart.hypr_request("j/activewindow"), "ok")
        self.factory.assert_called_once_with(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connection.connect.assert_called_once_with("/isolated/runtime/hypr/instance-test/.socket.sock")
        self.connection.sendall.assert_called_once_with(b"j/activewindow")
        self.assertEqual(self.connection.recv.call_count, 2)
        for timeout in self.connection.settimeout.call_args_list:
            self.assertAlmostEqual(timeout.args[0], 0.025)
        self.assert_closed()

    def test_fragmented_utf8_response_reads_until_eof_and_closes(self) -> None:
        self.connection.recv.side_effect = [b"{\"title\":\"", b"\xe2", b"\x82\xac\"}", b""]
        self.assertEqual(self.smart.hypr_request("j/activewindow"), '{"title":"€"}')
        self.assertEqual(self.connection.recv.call_count, 4)
        self.connection.sendall.assert_called_once()
        self.assert_closed()

    def test_empty_eof_response_is_valid_and_closes(self) -> None:
        self.connection.recv.side_effect = [b""]
        self.assertEqual(self.smart.hypr_request("j/activewindow"), "")
        self.assert_closed()

    def test_missing_or_empty_environment_does_not_create_socket(self) -> None:
        for name in ("XDG_RUNTIME_DIR", "HYPRLAND_INSTANCE_SIGNATURE"):
            for value in (None, ""):
                with self.subTest(name=name, value=value), patch.dict(os.environ):
                    if value is None:
                        os.environ.pop(name)
                    else:
                        os.environ[name] = value
                    self.assertIsNone(self.smart.hypr_request("j/activewindow"))
        self.factory.assert_not_called()
        self.connection.connect.assert_not_called()

    def test_socket_creation_oserror_is_silent(self) -> None:
        self.factory.side_effect = OSError("socket unavailable")
        self.assertIsNone(self.smart.hypr_request("j/activewindow"))
        self.factory.assert_called_once()

    def test_connect_send_and_read_timeout_or_oserror_close_without_retry(self) -> None:
        for stage in ("connect", "sendall", "recv"):
            for error in (TimeoutError("deadline"), OSError("IPC failed")):
                with self.subTest(stage=stage, error=type(error).__name__):
                    self.connection = RecordingSocket()
                    self.factory.reset_mock()
                    self.factory.return_value = self.connection
                    getattr(self.connection, stage).side_effect = error
                    self.assertIsNone(self.smart.hypr_request("j/activewindow"))
                    self.factory.assert_called_once()
                    getattr(self.connection, stage).assert_called_once()
                    if stage == "connect":
                        self.connection.sendall.assert_not_called()
                    if stage != "recv":
                        self.connection.recv.assert_not_called()
                    self.assert_closed()

    def test_total_deadline_shrinks_across_connect_send_and_slow_fragments(self) -> None:
        now = 100.0

        def monotonic() -> float:
            return now

        def connect(path: str) -> None:
            nonlocal now
            now += 0.006

        def send(data: bytes) -> None:
            nonlocal now
            now += 0.004

        def recv(size: int) -> bytes:
            nonlocal now
            now += 0.010 if self.connection.recv.call_count == 1 else 0.006
            return b"x"

        self.clock.side_effect = monotonic
        self.connection.connect.side_effect = connect
        self.connection.sendall.side_effect = send
        self.connection.recv.side_effect = recv
        self.assertIsNone(self.smart.hypr_request("j/activewindow"))
        timeouts = [entry.args[0] for entry in self.connection.settimeout.call_args_list]
        self.assertEqual(len(timeouts), 4)
        for actual, expected in zip(timeouts, (0.025, 0.019, 0.015, 0.005)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(self.connection.recv.call_count, 2, "slow fragments must not restart 25ms budget")
        self.assert_closed()

    def test_expired_connect_budget_prevents_send(self) -> None:
        self.clock.side_effect = [100.0, 100.0, 100.026]
        self.assertIsNone(self.smart.hypr_request("j/activewindow"))
        self.connection.connect.assert_called_once()
        self.connection.sendall.assert_not_called()
        self.assert_closed()

    def test_eof_after_total_deadline_is_not_accepted(self) -> None:
        now = 100.0

        def monotonic() -> float:
            return now

        def recv(size: int) -> bytes:
            nonlocal now
            now += 0.026
            return b""

        self.clock.side_effect = monotonic
        self.connection.recv.side_effect = recv
        self.assertIsNone(self.smart.hypr_request("j/activewindow"))
        self.assert_closed()

    def test_malformed_utf8_returns_none_and_closes(self) -> None:
        self.connection.recv.side_effect = [b"\xff", b""]
        self.assertIsNone(self.smart.hypr_request("j/activewindow"))
        self.assert_closed()

    def test_response_at_65536_byte_limit_is_accepted(self) -> None:
        self.connection.recv.side_effect = [b"x" * 4096] * 16 + [b""]
        self.assertEqual(self.smart.hypr_request("j/activewindow"), "x" * 65536)
        self.assert_closed()

    def test_oversize_response_returns_none_with_bounded_reads(self) -> None:
        self.connection.recv.side_effect = [b"x" * 4096] * 16 + [b"x"]
        self.assertIsNone(self.smart.hypr_request("j/activewindow"))
        self.assertEqual(self.connection.recv.call_count, 17)
        for entry in self.connection.recv.call_args_list:
            self.assertGreater(entry.args[0], 0)
            self.assertLessEqual(entry.args[0], 4096)
        self.assert_closed()

    def test_dispatched_eval_with_lost_reply_is_not_resent(self) -> None:
        request = expected_eval("left")
        self.connection.recv.side_effect = TimeoutError("reply lost after dispatch")
        self.assertIsNone(self.smart.hypr_request(request))
        self.factory.assert_called_once()
        self.connection.sendall.assert_called_once_with(request.encode("utf-8"))
        self.connection.recv.assert_called_once()
        self.assert_closed()


class SmartFocusMapsTest(unittest.TestCase):
    def test_exact_four_kitten_maps_keep_layout_fallback(self) -> None:
        focus_maps = [line for line in CONFIG.read_text().splitlines()
                      if line.startswith("map ") and " alt+" in line]
        self.assertEqual(focus_maps, [
            "map --allow-fallback=shifted,ascii alt+j kitten smart-focus.py left",
            "map --allow-fallback=shifted,ascii alt+l kitten smart-focus.py right",
            "map --allow-fallback=shifted,ascii alt+i kitten smart-focus.py up",
            "map --allow-fallback=shifted,ascii alt+k kitten smart-focus.py down",
        ])

    def test_resize_fallback_maps_and_native_generator_are_unchanged(self) -> None:
        lines = CONFIG.read_text().splitlines()
        resize_maps = [line for line in lines if line.startswith("map ") and " ctrl+alt+" in line
                       and "absolute-resize.py" in line]
        self.assertEqual(resize_maps, [
            "map --allow-fallback=shifted,ascii ctrl+alt+j remote_control_script absolute-resize.py left",
            "map --allow-fallback=shifted,ascii ctrl+alt+l remote_control_script absolute-resize.py right",
            "map --allow-fallback=shifted,ascii ctrl+alt+i remote_control_script absolute-resize.py up",
            "map --allow-fallback=shifted,ascii ctrl+alt+k remote_control_script absolute-resize.py down",
        ])
        generators = [line.split(maxsplit=1)[1] for line in lines
                      if line.startswith("geninclude ")]
        self.assertEqual(len(generators), 1)
        generator = Path(generators[0])
        if not generator.is_absolute():
            generator = CONFIG.parent / generator
        self.assertEqual(generator.resolve(), CONFIG.with_name("native-resize-maps.py").resolve())


def run_loader_smoke() -> None:
    """Real loader/decorator/Boss dispatch; stub only focus and IPC seams."""
    import kittens.runner as runner
    import kitty.boss as boss_module

    check = unittest.TestCase()
    original_import = runner.import_kitten_main_module
    loaded: list[dict[str, Any]] = []
    starts: list[Mock] = []

    def instrument_import(config_dir: str, kitten: str) -> dict[str, Any]:
        module = original_import(config_dir, kitten)
        main = Mock(spec=module["start"], side_effect=AssertionError("no-UI kitten must not call main"))
        starts.append(main)
        module["start"] = main
        globals_ = module["end"].impl.__globals__
        globals_["current_focused_os_window_id"] = Mock(return_value=11)
        globals_["hypr_request"] = Mock(side_effect=[json.dumps(source()), "ok"])
        loaded.append(module)
        return module

    with ExitStack() as stack:
        forbid_processes(stack)
        stack.enter_context(patch.object(runner, "import_kitten_main_module", side_effect=instrument_import))
        stack.enter_context(patch("socket.socket", side_effect=AssertionError("IPC seam only; no live sockets")))
        for direction, edge in DIRECTIONS:
            boss = fake_boss(neighbor=19)
            check.assertIsNone(boss_module.Boss.run_kitten_with_metadata(boss, str(SCRIPT), [direction]))
            check.assertTrue(loaded[-1]["end"].no_ui)
            boss.active_tab.neighboring_group_id.assert_called_once_with(edge)
            boss.active_tab.windows.set_active_group.assert_called_once_with(19)
            loaded[-1]["end"].impl.__globals__["hypr_request"].assert_not_called()

            boss = fake_boss()
            check.assertIsNone(boss_module.Boss.run_kitten_with_metadata(boss, str(SCRIPT), [direction]))
            boss.active_tab.neighboring_group_id.assert_called_once_with(edge)
            boss.active_tab.windows.set_active_group.assert_not_called()
            check.assertEqual(loaded[-1]["end"].impl.__globals__["hypr_request"].call_args_list,
                              [call("j/activewindow"), call(expected_eval(direction))])

        metadata = runner.create_kitten_handler(str(SCRIPT), ["left"])
        check.assertTrue(metadata.no_ui)
        check.assertFalse(metadata.allow_remote_control)
        boss = fake_boss()
        globals_ = loaded[-1]["end"].impl.__globals__
        globals_["current_focused_os_window_id"].return_value = 12
        metadata.handle_result(None, 7, boss)
        boss.active_tab.neighboring_group_id.assert_not_called()
        globals_["hypr_request"].assert_not_called()

        # A failed query does nothing; a lost eval reply never causes another dispatch.
        for responses, expected in (([None], [call("j/activewindow")]),
                                    ([json.dumps(source()), None], [call("j/activewindow"), call(expected_eval("down"))])):
            metadata = runner.create_kitten_handler(str(SCRIPT), ["down"])
            transport = loaded[-1]["end"].impl.__globals__["hypr_request"]
            transport.side_effect = responses
            boss = fake_boss()
            check.assertIsNone(metadata.handle_result(None, 7, boss))
            check.assertEqual(transport.call_args_list, expected)
            boss.show_error.assert_not_called()
            boss.active_tab.windows.set_active_group.assert_not_called()

    for main in starts:
        main.assert_not_called()
    print("LOADER SMOKE PASS: actual no_ui loader/Boss dispatch; 4 zero-IPC neighbors, 4 ordered PID+address edges, OS-focus guard, query/eval failure; no main, processes, background API or live sockets")


if __name__ == "__main__":
    unittest.main()
