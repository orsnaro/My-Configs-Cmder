"""Short-lived owned GTK sink for explicit synthetic input/click tests only."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

EXPRESSION = '123456789+987654321'


class Sink(Gtk.Application):
    def __init__(self, output: Path) -> None:
        super().__init__(application_id=f'org.opencode.RofiProbe.p{os.getpid()}')
        self.output = output
        self.state: dict[str, object] = {'prefix': '', 'clicks': 0, 'unexpected_input': False}
        self.connect('activate', self.activate_window)

    def save(self) -> None:
        temporary = self.output.with_suffix('.pending')
        temporary.write_text(json.dumps(self.state)+'\n')
        temporary.replace(self.output)

    def changed(self, entry: Gtk.Entry) -> None:
        text = entry.get_text()
        # Never record arbitrary text if the operator intervenes in the probe.
        if EXPRESSION.startswith(text):
            self.state['prefix'] = text
        else:
            self.state['unexpected_input'] = True
        self.save()

    def clicked(self, gesture: Gtk.GestureClick, count: int, x: float, y: float) -> None:
        self.state['clicks'] = int(self.state['clicks'])+1
        self.save()

    def activate_window(self, application: Gtk.Application) -> None:
        window = Gtk.ApplicationWindow(application=application, title=f'Owned Rofi input probe {os.getpid()}')
        window.set_default_size(600, 240)
        entry = Gtk.Entry()
        entry.set_placeholder_text('Synthetic Rofi test — do not type here')
        entry.connect('changed', self.changed)
        gesture = Gtk.GestureClick()
        gesture.set_button(0)
        gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        gesture.connect('pressed', self.clicked)
        window.add_controller(gesture)
        window.set_child(entry)
        window.present()
        entry.grab_focus()
        self.save()


if __name__ == '__main__':
    raise SystemExit(Sink(Path(sys.argv[1])).run([]))
