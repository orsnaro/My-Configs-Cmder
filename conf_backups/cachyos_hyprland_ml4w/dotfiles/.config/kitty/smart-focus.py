"""Focus native Kitty neighbors in-process; use bounded local IPC at an edge."""

from __future__ import annotations

import json
import os
import re
import socket
import time
from typing import TYPE_CHECKING, Literal

from kittens.tui.handler import result_handler
from kitty.fast_data_types import current_focused_os_window_id

if TYPE_CHECKING:
    from kitty.boss import Boss


KITTY_DIRECTIONS: dict[str, Literal["left", "right", "top", "bottom"]] = {
    "left": "left",
    "right": "right",
    "up": "top",
    "down": "bottom",
}
REQUEST_TIMEOUT = 0.025
RESPONSE_LIMIT = 65536


def main(args: list[str]) -> None:
    pass


def hypr_request(request: str) -> str | None:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not runtime_dir or not signature:
        return None

    deadline = time.monotonic() + REQUEST_TIMEOUT
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            def set_timeout() -> None:
                # Fragments share the same request budget, never a fresh timeout.
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                connection.settimeout(remaining)

            set_timeout()
            connection.connect(os.path.join(runtime_dir, "hypr", signature, ".socket.sock"))
            set_timeout()
            connection.sendall(request.encode("utf-8"))
            response = bytearray()
            while True:
                set_timeout()
                chunk = connection.recv(min(4096, RESPONSE_LIMIT + 1 - len(response)))
                if time.monotonic() >= deadline:
                    return None
                if not chunk:
                    return response.decode("utf-8")
                if len(response) + len(chunk) > RESPONSE_LIMIT:
                    return None
                response.extend(chunk)
    except (OSError, UnicodeError):
        return None


def focus_desktop(direction: str) -> None:
    if direction not in KITTY_DIRECTIONS:
        return
    reply = hypr_request("j/activewindow")
    if reply is None:
        return
    try:
        source = json.loads(reply)
    except ValueError:
        return
    if not isinstance(source, dict):
        return
    pid = os.getpid()
    if source.get("pid") != pid or source.get("class") not in ("kitty", "quake-kitty"):
        return
    address = source.get("address")
    if not isinstance(address, str) or re.fullmatch(r"0x[0-9a-fA-F]+", address) is None:
        return
    # Never retry: a missing reply can follow a successful focus change.
    hypr_request(f'/eval checked_focus("{direction}", {pid}, "{address}")')


@result_handler(no_ui=True)
def handle_result(args: list[str], data: None, target_window_id: int, boss: Boss) -> None:
    if len(args) != 2:
        return
    direction = args[1]
    edge = KITTY_DIRECTIONS.get(direction)
    if edge is None:
        return

    tab = boss.active_tab
    window = boss.active_window
    if tab is None or window is None or window.id != target_window_id:
        return
    if current_focused_os_window_id() != tab.os_window_id:
        return

    neighbor = tab.neighboring_group_id(edge)
    if neighbor is not None:
        tab.windows.set_active_group(neighbor)
        return

    focus_desktop(direction)
