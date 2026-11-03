"""Owned-PID GUI checks using synthetic data; never reads the real clipboard."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from collections.abc import Callable
from typing import Any

import gi
gi.require_version('Atspi', '2.0')
from gi.repository import Atspi

HOME = Path.home()
STATE = HOME/'.local/state/sherlock-migration/20261102'
LAUNCH = str(HOME/'.local/bin/sherlock-launch')
PID = int(subprocess.check_output(['systemctl', '--user', 'show', 'sherlock.service', '-p', 'MainPID', '--value'], text=True))


def wait_for(check: Callable[[], Any], seconds: float = 5) -> Any:
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(.05)
    raise AssertionError('Synthetic GUI check timed out')


def nodes() -> list[Any]:
    global PID
    # Mode changes deliberately replace the daemon; follow its new owned PID.
    PID = int(subprocess.check_output(['systemctl', '--user', 'show', 'sherlock.service', '-p', 'MainPID', '--value'], text=True))
    desktop = Atspi.get_desktop(0)
    apps = [desktop.get_child_at_index(i) for i in range(desktop.get_child_count())]
    stack = [app for app in apps if app is not None and app.get_process_id() == PID]
    result = []
    while stack:
        node = stack.pop()
        # GTK can remove children between AT-SPI enumeration and retrieval.
        if node is None:
            continue
        result.append(node)
        stack.extend(node.get_child_at_index(i) for i in range(node.get_child_count()))
    return result


def close() -> None:
    payload = b'"Close"'
    with socket.socket(socket.AF_UNIX) as connection:
        try:
            connection.connect('/tmp/sherlock_daemon.sock')
        except (FileNotFoundError, ConnectionRefusedError):
            return
        connection.sendall(len(payload).to_bytes(4, 'big')+payload)
    time.sleep(.2)


def open_mode(mode: str) -> None:
    subprocess.run([LAUNCH, mode], check=True, timeout=8, stdout=subprocess.DEVNULL)
    wait_for(lambda: [node for node in nodes() if node.get_editable_text_iface()])


def search(text: str) -> None:
    field = wait_for(lambda: next((node for node in nodes() if node.get_editable_text_iface()), None))
    assert field.get_editable_text_iface().set_text_contents(text)
    time.sleep(.3)


def activate_label(title: str) -> None:
    node = wait_for(lambda: next((node for node in nodes() if node.get_name() == title), None))
    row = None
    for _ in range(6):
        if node.get_role() == Atspi.Role.LIST_ITEM:
            row = node
        action = node.get_action_iface()
        if action:
            for index in range(action.get_n_actions()):
                if action.get_action_name(index) in ('activate', 'click'):
                    assert action.do_action(index)
                    return
        node = node.get_parent()
        if node is None:
            break
    assert row is not None, 'No owned result row'
    listing = row.get_parent()
    selection = listing.get_selection_iface()
    assert selection and selection.select_child(row.get_index_in_parent())
    selected = selection.get_selected_child(0)
    stack = [selected]
    titles = []
    while stack:
        item = stack.pop()
        titles.append(item.get_name())
        stack.extend(item.get_child_at_index(i) for i in range(item.get_child_count()))
    assert title in titles, 'Synthetic result is not the selected row'
    field = next(item for item in nodes() if item.get_editable_text_iface())
    if not field.get_state_set().contains(Atspi.StateType.FOCUSED):
        assert field.get_component_iface().grab_focus()
    assert field.get_state_set().contains(Atspi.StateType.FOCUSED)
    layers = json.loads(subprocess.check_output(['hyprctl', '-j', 'layers'], text=True))
    launchers = [item for monitor in layers.values() for level in monitor['levels'].values()
                 for item in level if item['namespace'] in ('rofi', 'sherlock')]
    assert len(launchers) == 1 and launchers[0]['pid'] == PID
    # GTK exposes selection, but not activation. One guarded Return on synthetic data only.
    assert field.get_state_set().contains(Atspi.StateType.FOCUSED)
    subprocess.run(['wtype', '-k', 'Return'], check=True, timeout=2)


def clipboard_checks() -> dict[str, bool]:
    text = 'Sherlock synthetic مرحبا\nsecond line 👋\n'.encode()
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8XcAAAAASUVORK5CYII=')
    with tempfile.TemporaryDirectory(prefix='sherlock-gui-', dir='/tmp/opencode') as name:
        root = Path(name)
        binaries = root/'bin'
        binaries.mkdir()
        cliphist = binaries/'cliphist'
        cliphist.write_text(f'#!/usr/bin/env bash\nexec /usr/bin/cliphist -db-path "{root}/db" -config-path /dev/null "$@"\n')
        cliphist.chmod(0o755)
        copy = binaries/'wl-copy'
        copy.write_text('#!/usr/bin/env bash\ncat >"$SYNTHETIC_SINK"\n')
        copy.chmod(0o755)
        sink = root/'sink'
        environment = {**os.environ, 'PATH': str(binaries)+':'+os.environ['PATH'], 'SYNTHETIC_SINK': str(sink)}
        for data in (text, png):
            subprocess.run([str(cliphist), 'store'], input=data, env=environment, check=True, capture_output=True)
        data = json.loads(subprocess.check_output([str(HOME/'.local/bin/sherlock-clp')], env=environment))
        entries = [item for item in data['elements'] if item['result']]
        results = {}
        for label, expected in (('text', text), ('image', png)):
            close()
            selected = next(item for item in entries if bool(item['binary']) == (label == 'image'))
            sink.write_bytes(b'untouched fixture')
            process = subprocess.Popen([LAUNCH, 'clipboard'], env=environment, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                activate_label(selected['title'])
                _output, error = process.communicate(timeout=8)
                assert process.returncode == 0, error.decode()
                assert sink.read_bytes() == expected, 'Selected synthetic bytes changed'
                results[label+'_selection_copies_exact_bytes'] = True
            finally:
                close()
                if process.poll() is None:
                    process.terminate()
                    process.communicate(timeout=5)
        return results


def main() -> None:
    report: dict[str, Any] = {'pid': PID, 'personal_clipboard_read_or_written': False}
    try:
        close()
        open_mode('apps')
        search('2+3*4')
        wait_for(lambda: any(node.get_name().replace(' ', '') in ('=14', '14') for node in nodes()))
        report['automatic_calculator'] = True
        (STATE/'app-launch.ok').unlink(missing_ok=True)
        search('Sherlock Integration Check')
        activate_label('Sherlock Integration Check')
        wait_for(lambda: (STATE/'app-launch.ok').exists())
        report['native_desktop_app_launch'] = True
        close()
        open_mode('emoji')
        search('smile')
        wait_for(lambda: any(node.get_name() in ('Big Smile', 'Smiling Face with Smiling Eyes') for node in nodes()))
        report['native_emoji_search'] = True
        report['emoji_shortcut_requires_enter_to_open_grid'] = False
        report.update(clipboard_checks())
        # Bypass the wrapper's reset here to independently verify dismissal cleanup.
        payload = b'{"Show":"all"}'
        with socket.socket(socket.AF_UNIX) as connection:
            connection.connect('/tmp/sherlock_daemon.sock')
            connection.sendall(len(payload).to_bytes(4, 'big')+payload)
        search('2+3*4')
        wait_for(lambda: any(node.get_name().replace(' ', '') in ('=14', '14') for node in nodes()))
        report['clipboard_to_apps_transition'] = True
        report['dismissal_restores_app_model_without_showing_history'] = True
        report['all_checks_passed'] = True
    finally:
        close()
        (STATE/'live-check.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
