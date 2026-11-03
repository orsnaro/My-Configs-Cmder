"""Exercise the public desktop backup with private-state decoys and a fresh HOME."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2] / 'conf_backups/cachyos_hyprland_ml4w'


class ConfigRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='config-refresh-', dir='/tmp/opencode')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'new home'
        self.home.mkdir()
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        for name in ('BACKUP.sh', 'RESTORE.sh'):
            shutil.copy2(SOURCE / name, self.bundle / name)
        self.env = {**os.environ, 'HOME': str(self.home)}

    def write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_backup_carries_launcher_and_mail_source_without_private_state(self) -> None:
        for name in ('hypr', 'kitty', 'quickshell', 'waybar', 'rofi', 'swaync', 'ml4w'):
            self.write(self.home, f'.config/{name}/fixture', 'public\n')
        public = {
            '.config/sherlock/config.toml': '[appearance]\nicon_size = 53\n',
            '.config/systemd/user/sherlock.service': '[Service]\nExecStart=%h/.local/bin/sherlock\n',
            '.local/bin/sherlock-launch': '#!/bin/bash\nexit 0\n',
            '.local/share/sherlock-integration/sherlock_ipc.py': '# public source\n',
            '.local/src/glaze-mail/session.py': '# public source\n',
            '.config/glaze-mail/terminal/config/aerc/binds.conf': '[messages]\n',
            '.config/glaze-mail/eval/lesskey': '#command\n',
        }
        private = (
            '.config/glaze-mail/eval/accounts.conf',
            '.config/glaze-mail/terminal/config/BraveSoftware/Brave-Browser/Local State',
            '.local/src/glaze-mail/Drafts/message.eml',
            '.local/share/sherlock-integration/upstream-clipboard/target/release/sherlock-clp',
            '.local/share/sherlock-integration/sherlock-v0.1.14-3-bin-linux-x86_64.tar.gz',
        )
        for name, text in public.items():
            self.write(self.home, name, text)
        for name in private:
            self.write(self.home, name, 'PRIVATE DECOY\n')
        result = subprocess.run(['bash', str(self.bundle / 'BACKUP.sh')], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, text in public.items():
            prefix = 'dotfiles/' if name.startswith('.config/') else 'local/'
            target = self.bundle / prefix / name
            self.assertTrue(target.is_file(), f'missing public dependency: {name}')
            self.assertEqual(target.read_text(), text)
        for path in self.bundle.rglob('*'):
            if path.is_file():
                self.assertNotIn(b'PRIVATE DECOY', path.read_bytes(), str(path))

    def test_restore_rebases_sherlock_and_copies_mail_without_activation(self) -> None:
        self.write(self.bundle, 'dotfiles/.config/sherlock/config.toml',
                   '[files]\nconfig = "/home/narol/.config/sherlock/config.toml"\n')
        self.write(self.bundle, 'dotfiles/.config/sherlock/main.css',
                   '@import url("file:///home/narol/.config/gtk-4.0/colors.css");\n')
        self.write(self.bundle, 'dotfiles/.config/systemd/user/sherlock.service', '[Service]\n')
        self.write(self.bundle, 'local/.local/share/sherlock-integration/sherlock_ipc.py', '# helper\n')
        self.write(self.bundle, 'local/.local/src/glaze-mail/session.py', '# mail\n')
        self.write(self.bundle, 'dotfiles/.config/glaze-mail/eval/lesskey', '#command\n')
        self.write(self.bundle, 'local/.local/share/applications/aerc-mail.desktop',
                   '[Desktop Entry]\nType=Application\nName=Mail\nExec=/home/narol/.local/bin/glaze-mail\n')
        commands = self.root / 'commands'
        for name in ('systemctl', 'hyprctl', 'sherlock', 'brave'):
            command = self.write(commands, name, '#!/bin/sh\necho called >> "$HOME/activated"\nexit 99\n')
            command.chmod(0o755)
        result = subprocess.run(['bash', str(self.bundle / 'RESTORE.sh')],
                                env={**self.env, 'PATH': f'{commands}:/usr/bin:/bin'},
                                input='n\n', capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.home / '.config/sherlock/config.toml'
        self.assertTrue(config.is_file(), 'Sherlock configuration was not restored')
        self.assertIn(str(self.home), config.read_text())
        self.assertNotIn('/home/narol/', config.read_text())
        self.assertIn(f'file://{self.home}/.config/gtk-4.0/colors.css',
                      (self.home / '.config/sherlock/main.css').read_text())
        self.assertTrue((self.home / '.config/systemd/user/sherlock.service').is_file())
        self.assertTrue((self.home / '.local/share/sherlock-integration/sherlock_ipc.py').is_file())
        self.assertTrue((self.home / '.local/src/glaze-mail/session.py').is_file())
        entry = (self.home / '.local/share/applications/aerc-mail.desktop').read_text()
        command = next(line.removeprefix('Exec=') for line in entry.splitlines() if line.startswith('Exec='))
        self.assertEqual(shlex.split(command), [str(self.home / '.local/bin/glaze-mail')])
        self.assertEqual((self.home / '.config/glaze-mail/eval/lesskey').stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.home / 'activated').exists())

    def test_dry_run_does_not_rebase_or_create_home_files(self) -> None:
        self.write(self.bundle, 'dotfiles/.config/sherlock/config.toml',
                   '[files]\nconfig = "/home/narol/.config/sherlock/config.toml"\n')
        result = subprocess.run(['bash', str(self.bundle / 'RESTORE.sh'), '--dry-run'],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_absent_payload_does_not_rewrite_existing_preferences(self) -> None:
        path = self.write(self.home, '.config/sherlock/config.toml',
                          '[files]\nconfig = "/home/narol/keep-my-setting"\n')
        result = subprocess.run(['bash', str(self.bundle / 'RESTORE.sh')], env=self.env,
                                input='n\n', capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('/home/narol/keep-my-setting', path.read_text())


if __name__ == '__main__':
    unittest.main()
