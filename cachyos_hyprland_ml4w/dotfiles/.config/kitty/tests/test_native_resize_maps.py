"""Config-load notification for a missing native Kitty edit."""

import contextlib
import io
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch


GENERATOR = Path(__file__).resolve().parents[1] / 'native-resize-maps.py'


class NativeResizeMapsTest(unittest.TestCase):
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
