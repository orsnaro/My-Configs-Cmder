"""Install and execute guarded hooks in an isolated home, never the live session."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tools import install_desktop_stack as install


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir='/tmp/opencode', prefix='stack-install-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home with spaces'
        self.home.mkdir()
        self.repo = self.root / 'repo with spaces'
        (self.repo / 'tools').mkdir(parents=True)
        for name in ('desktop_stack.py', 'switch-to-qs.sh', 'switch-to-pleamar.sh'):
            (self.repo / 'tools' / name).write_text('fixture\n')
        self.write('.config/hypr/conf/autostart.lua', '''hl.on("hyprland.start", function ()
    local HOME = os.getenv("HOME")
    hl.exec_cmd("systemctl --user start pleamar.service")
    hl.exec_cmd("vitreus-keep " .. HOME .. "/lockscreen/lockscreen.plm")
    hl.exec_cmd("hypridle")
end)
''')
        self.write('.config/hypr/hyprland.lua', '''local vitreus_binds = io.open(os.getenv("HOME") .. "/.config/hypr/hypr_vitreus.lua", "r")
if vitreus_binds then
    vitreus_binds:close()
    require("hypr_vitreus")
end
pcall(require, "vitreus_monitors")
pcall(require, "vitreus_hypr")
pcall(require, "vitreus_colors")
''')
        self.write('.config/systemd/user/pleamar.service', '[Service]\nExecStart=/fixture/pleamar-start\n')
        self.write('.config/ml4w/scripts/ml4w-autostart', '#!/bin/bash\nnm-applet --indicator &\nqs &\nml4w-dock start &\n')
        self.write('.local/bin/qs-lazy-toggle', '#!/bin/bash\nqs -n -p fixture\n')
        self.write('.config/ml4w/scripts/ml4w-wallpaper-automation', '#!/bin/bash\necho automation >> "$LOG"\n')
        self.write('.config/ml4w/scripts/ml4w-toggle-hyprsunset', '#!/bin/bash\npleamar --say vitreus "emit night_toggle"\n')
        self.write('.config/ml4w/scripts/ml4w-wallpaper-app', '''#!/bin/bash
if [ "$1" == --random ]; then echo wallpaper >> "$LOG"; exit; fi
# Launch wallpaper app
if [ "$WALLPAPER_APP" == "quickshell" ]; then
    qs ipc call wallpaper toggle
fi
''')
        self.write('.config/ml4w/scripts/ml4w-wallpaper', '#!/bin/bash\n' + '\n'.join(
            f'reload_{name}() {{\n    {command}\n}}' for name, command in
            (('waybar', 'waybar'), ('quickshell', 'qs'), ('swaync', 'swaync'), ('walker', 'walker'))
        ) + '\nreload_waybar\nreload_quickshell\nreload_swaync\nreload_walker\n')
        branch = '''qs ipc call theme-manager reload
qs -p "$HOME/settings" ipc call theme-manager reload
nohup bash -c "$HOME/.config/waybar/launch.sh" > /dev/null 2>&1 &
disown
if pgrep -x swaync >/dev/null 2>&1; then swaync-client -rs; fi
if command -v walker >/dev/null 2>&1; then
    pkill -x walker 2>/dev/null
    walker --gapplication-service >/dev/null 2>&1 &
fi
'''
        self.write('.config/ml4w/listeners/gtk-theme-switcher.sh', '#!/bin/bash\n' + branch + branch)
        for name in install.QS_HELPERS:
            self.write('.config/ml4w/scripts/' + name, '#!/bin/bash\nqs ipc call dock toggle\n')
        self.write('.config/ml4w/settings/wallpaper-slideshow', 'true\n')
        self.write('.config/ml4w/settings/waybar-disabled', '')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name in ('qs', 'walker', 'elephant', 'waybar', 'swaync', 'swaync-client', 'pkill', 'nm-applet', 'ml4w-dock', 'pleamar', 'hyprsunset', 'hyprctl'):
            path = self.bin / name
            path.write_text('#!/bin/bash\necho "${0##*/} $*" >> "$LOG"\n')
            path.chmod(0o755)
        self.write('.config/waybar/launch.sh', '#!/bin/bash\necho waybar >> "$LOG"\n')
        (self.bin / 'pgrep').write_text('#!/bin/bash\nexit 0\n')
        (self.bin / 'pgrep').chmod(0o755)
        self.log = self.root / 'calls'
        self.env = {**os.environ, 'HOME': str(self.home), 'PATH': f'{self.bin}:/usr/bin:/bin', 'LOG': str(self.log), 'WALLPAPER_APP': 'quickshell'}

    def write(self, name: str, text: str) -> Path:
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def apply(self) -> dict[str, object]:
        return install.install(self.home, self.repo, apply=True)

    def test_preview_writes_nothing(self) -> None:
        before = {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        result = install.install(self.home, self.repo)
        self.assertFalse(result['applied'])
        self.assertEqual(before, {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        self.assertFalse((self.home / '.local/state').exists())

    def test_install_is_idempotent_and_never_activates_anything(self) -> None:
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('installer must not run commands')), mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('installer must not spawn')):
            result = self.apply()
            again = self.apply()
        self.assertTrue(result['applied'])
        self.assertEqual(again['changed'], [])
        self.assertEqual((self.home / '.config/ml4w/settings/desktop-stack').read_text(), 'pleamar\n')
        self.assertEqual((self.home / '.config/ml4w/settings/wallpaper-slideshow').read_text(), 'true\n')
        checkpoint = Path(str(result['checkpoint']))
        self.assertEqual(checkpoint.stat().st_mode & 0o777, 0o700)

    def test_two_launchers_and_links_work_with_spaced_paths(self) -> None:
        self.apply()
        apps = list((self.home / '.local/share/applications').glob('*.desktop'))
        self.assertEqual(len(apps), 2)
        for mode in ('qs', 'pleamar'):
            text = (self.home / f'.local/share/applications/switch-to-{mode}.desktop').read_text()
            self.assertIn(f'Exec="{self.home}/.local/bin/switch-to-{mode}"', text)
            self.assertTrue((self.home / f'.local/bin/switch-to-{mode}').is_symlink())

    def test_root_alias_and_shared_monitor_settings_are_preserved(self) -> None:
        source = self.home / '.config/hypr'
        target = self.home / 'hypr-real'
        source.rename(target)
        source.symlink_to(target, target_is_directory=True)
        self.apply()
        self.assertTrue(source.is_symlink())
        text = (source / 'hyprland.lua').read_text()
        self.assertIn('pcall(require, "vitreus_monitors")', text)
        self.assertIn('desktop_stack_mode', text)
        self.assertIn('ExecCondition=', (self.home / '.config/systemd/user/pleamar.service').read_text())

    def test_guarded_hooks_cannot_resurrect_inactive_stack(self) -> None:
        self.apply()
        paths = ('.config/ml4w/scripts/ml4w-autostart', '.local/bin/qs-lazy-toggle',
                 '.config/ml4w/scripts/ml4w-wallpaper-automation', '.config/ml4w/scripts/ml4w-wallpaper',
                 '.config/ml4w/listeners/gtk-theme-switcher.sh')
        for name in paths:
            with self.subTest(path=name):
                result = subprocess.run(['bash', str(self.home / name), '--start'], env=self.env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists(), self.log.read_text() if self.log.exists() else '')
        (self.home / '.config/ml4w/settings/desktop-stack').write_text('quickshell\n')
        result = subprocess.run(['bash', str(self.home / '.config/ml4w/scripts/ml4w-wallpaper')], env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('walker', self.log.read_text())

    def test_shared_wallpaper_random_and_qs_night_mode_do_not_call_pleamar(self) -> None:
        self.apply()
        app = self.home / '.config/ml4w/scripts/ml4w-wallpaper-app'
        result = subprocess.run(['bash', str(app), '--random'], env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text(), 'wallpaper\n')
        self.log.unlink()
        (self.home / '.config/ml4w/settings/desktop-stack').write_text('quickshell\n')
        result = subprocess.run(['bash', str(self.home / '.config/ml4w/scripts/ml4w-toggle-hyprsunset'), 'off'], env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('pleamar', self.log.read_text())

    def test_unexpected_shape_fails_before_any_file_write(self) -> None:
        path = self.write('.config/hypr/conf/autostart.lua', '-- unrelated config\n')
        with self.assertRaises(install.InstallError):
            self.apply()
        self.assertEqual(path.read_text(), '-- unrelated config\n')
        self.assertFalse((self.home / '.config/ml4w/settings/desktop-stack').exists())


if __name__ == '__main__':
    unittest.main()
