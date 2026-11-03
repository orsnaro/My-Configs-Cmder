"""Run both exported Hyprland suites without accessing the real desktop."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
ML4W = ROOT / 'conf_backups/cachyos_hyprland_ml4w'
PLEAMAR = ROOT / 'conf_backups/cachyos_hyprland_pleamar'


class HyprlandSnapshotTests(unittest.TestCase):
    def test_exported_suites_with_their_real_helpers(self) -> None:
        for overlay in (ML4W / 'dotfiles/.config/hypr', PLEAMAR / 'config/hypr'):
            with self.subTest(overlay=str(overlay)), tempfile.TemporaryDirectory(
                    prefix='hypr-snapshot-', dir='/tmp/opencode') as directory:
                home = Path(directory)
                shutil.copytree(ML4W / 'dotfiles/.config', home / '.config')
                shutil.copytree(overlay, home / '.config/hypr', dirs_exist_ok=True)
                shutil.copytree(ML4W / 'local/.local/bin', home / '.local/bin')
                config = home / '.config/hypr'
                env = {**os.environ, 'HOME': directory, 'LUA_PATH': f'{config}/?.lua;;'}
                tests = sorted(path for path in (config / 'tests').iterdir()
                               if path.suffix in {'.lua', '.sh'})
                self.assertGreaterEqual(len(tests), 19, 'snapshot lost its regression suite')
                tests.append(ML4W / 'local/.local/share/sherlock-integration/test_session.lua')
                for path in tests:
                    with self.subTest(test=path.name):
                        result = subprocess.run(['lua' if path.suffix == '.lua' else 'bash', str(path)],
                                                cwd=config, env=env, text=True, capture_output=True, timeout=30)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
