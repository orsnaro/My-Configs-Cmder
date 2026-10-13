"""Config-load notification for a missing native Kitty edit."""

import contextlib
import io
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from typing import Any
from unittest.mock import Mock, patch


GENERATOR = Path(__file__).resolve().parents[1] / 'native-resize-maps.py'
CONFIG = GENERATOR.with_name('custom.conf')


def load_generator() -> dict[str, Any]:
    """Keep module-level main() real, isolating its notification side effects."""
    with tempfile.TemporaryDirectory() as cache, \
            patch.dict(os.environ, XDG_CACHE_HOME=cache), \
            patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0)), \
            contextlib.redirect_stdout(io.StringIO()):
        return runpy.run_path(str(GENERATOR))


class NativeResizeMapsTest(unittest.TestCase):
    def test_native_maps_include_letter_and_arrow_aliases(self) -> None:
        generator = load_generator()
        output = io.StringIO()
        alert = Mock()
        with patch.dict(generator['main'].__globals__,
                        probe_native=Mock(return_value=True), maybe_alert=alert), \
                contextlib.redirect_stdout(output):
            self.assertEqual(generator['main'](), 0)

        self.assertEqual(output.getvalue(), '\n'.join([
            'map --allow-fallback=shifted,ascii ctrl+alt+j resize_divider left',
            'map --allow-fallback=shifted,ascii ctrl+alt+l resize_divider right',
            'map --allow-fallback=shifted,ascii ctrl+alt+i resize_divider up',
            'map --allow-fallback=shifted,ascii ctrl+alt+k resize_divider down',
            'map --allow-fallback=shifted,ascii ctrl+alt+left resize_divider left',
            'map --allow-fallback=shifted,ascii ctrl+alt+right resize_divider right',
            'map --allow-fallback=shifted,ascii ctrl+alt+up resize_divider up',
            'map --allow-fallback=shifted,ascii ctrl+alt+down resize_divider down',
        ]) + '\n')
        alert.assert_not_called()

    def test_stock_build_emits_no_native_maps_and_keeps_fallbacks(self) -> None:
        generator = load_generator()
        output = io.StringIO()
        alert = Mock()
        with patch.dict(generator['main'].__globals__,
                        probe_native=Mock(return_value=False), maybe_alert=alert), \
                contextlib.redirect_stdout(output):
            self.assertEqual(generator['main'](), 0)

        self.assertEqual(output.getvalue(), '')
        alert.assert_called_once_with(generator['source_hash']())
        fallback_maps = [line for line in CONFIG.read_text().splitlines()
                         if line.startswith('map ') and ' ctrl+alt+' in line
                         and 'absolute-resize.py' in line]
        self.assertEqual(fallback_maps, [
            'map --allow-fallback=shifted,ascii ctrl+alt+j remote_control_script absolute-resize.py left',
            'map --allow-fallback=shifted,ascii ctrl+alt+l remote_control_script absolute-resize.py right',
            'map --allow-fallback=shifted,ascii ctrl+alt+i remote_control_script absolute-resize.py up',
            'map --allow-fallback=shifted,ascii ctrl+alt+k remote_control_script absolute-resize.py down',
            'map --allow-fallback=shifted,ascii ctrl+alt+left remote_control_script absolute-resize.py left',
            'map --allow-fallback=shifted,ascii ctrl+alt+right remote_control_script absolute-resize.py right',
            'map --allow-fallback=shifted,ascii ctrl+alt+up remote_control_script absolute-resize.py up',
            'map --allow-fallback=shifted,ascii ctrl+alt+down remote_control_script absolute-resize.py down',
        ])

    def test_update_alert_is_conspicuous_and_once_per_source_hash(self):
        with tempfile.TemporaryDirectory() as cache, \
                patch.dict(os.environ, XDG_CACHE_HOME=cache), \
                patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as notify, \
                contextlib.redirect_stdout(io.StringIO()):
            generator = runpy.run_path(str(GENERATOR))
            # run_path executes module-level main(): on stock kitty it fires
            # one maybe_alert for the real source hash; discard it so the
            # assertions below only see the two explicit calls.
            notify.reset_mock()
            generator['maybe_alert']('stock-version-under-test')
            generator['maybe_alert']('stock-version-under-test')

            notify.assert_called_once()
            self.assertEqual(notify.call_args.args[0], [
                'notify-send', '--urgency=critical', '--expire-time=15000',
                '--app-name=kitty',
                '⚠️ WARNING!: Kitty update removed ORS native pans resize code edits!',
                generator['ALERT_BODY'],
            ])
            self.assertTrue((Path(cache) / 'kitty-ors-native-alert-stock-version-under-test').exists())


if __name__ == '__main__':
    unittest.main()
