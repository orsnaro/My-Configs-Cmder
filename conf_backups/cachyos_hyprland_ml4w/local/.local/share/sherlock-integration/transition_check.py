"""Real mode-switch and app-reopening checks; only synthetic clipboard data."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import live_check as probe


def current_pid() -> int:
    return int(subprocess.check_output(['systemctl', '--user', 'show', 'sherlock.service', '-p', 'MainPID', '--value'], text=True))


def geometry() -> list[dict[str, object]]:
    data = json.loads(subprocess.check_output(['hyprctl', '-j', 'layers'], text=True))
    return [{'monitor': name, **{key: row.get(key) for key in ('pid', 'w', 'h')}}
            for name, monitor in data.items() for level in monitor['levels'].values()
            for row in level if row['namespace'] == 'sherlock']


def cpu(pid: int) -> float:
    def ticks() -> int:
        fields = (Path('/proc')/str(pid)/'stat').read_text().split(') ', 1)[1].split()
        return int(fields[11])+int(fields[12])
    start = time.monotonic()
    before = ticks()
    time.sleep(2)
    return round((ticks()-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-start)*100, 3)


def check_calculator() -> None:
    probe.search('2+3*4')
    probe.wait_for(lambda: any(node.get_name().replace(' ', '') in ('=14', '14') for node in probe.nodes()))


def check_history_cancellation() -> None:
    probe.close()
    with tempfile.TemporaryDirectory(prefix='sherlock-cancel-', dir='/tmp/opencode') as name:
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
        sink.write_bytes(b'untouched fixture')
        environment = {**os.environ, 'PATH': str(binaries)+':'+os.environ['PATH'], 'SYNTHETIC_SINK': str(sink)}
        text = 'Sherlock cancelled history fixture'
        subprocess.run([str(cliphist), 'store'], input=text.encode(), env=environment, check=True, capture_output=True)
        process = subprocess.Popen([probe.LAUNCH, 'clipboard'], env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            probe.wait_for(lambda: any(node.get_name() == text for node in probe.nodes()))
            probe.open_mode('apps')
            _output, error = process.communicate(timeout=8)
            assert process.returncode == 0, error.decode()
            assert sink.read_bytes() == b'untouched fixture', 'Cancellation replaced the synthetic sink'
            check_calculator()
        finally:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=5)


def main() -> None:
    state = Path.home()/'.local/state/sherlock-migration/20261102/meta-fix'
    report: dict[str, object] = {'mode_cycles': 4, 'app_open_close_cycles': 40, 'personal_clipboard_read_or_written': False}
    try:
        report['stage'] = 'emoji/app cycles'
        for _ in range(4):
            probe.close()
            probe.open_mode('emoji')
            probe.search('smile')
            probe.wait_for(lambda: any(node.get_name() in ('Big Smile', 'Smiling Face with Smiling Eyes') for node in probe.nodes()))
            emoji_pid = current_pid()
            probe.close()
            probe.open_mode('apps')
            check_calculator()
            assert current_pid() != emoji_pid, 'Mode change reused the previously reloaded process'
        report['emoji_app_cycles_passed'] = True
        report['stage'] = 'cancel active synthetic history by reopening apps'
        check_history_cancellation()
        report['active_history_cancellation_passed'] = True
        report['stage'] = 'resident app open/close cycles'
        pid = current_pid()
        for _ in range(40):
            probe.close()
            subprocess.run([str(Path.home()/'.config/hypr/scripts/launcher.sh')], check=True, timeout=8,
                           stdout=subprocess.DEVNULL)
            probe.wait_for(lambda: any(row['pid'] == pid and row['w'] == 900 and row['h'] == 593 for row in geometry()))
            time.sleep(.06)
        report['app_pid_stable'] = current_pid() == pid
        report['app_pid'] = pid
        report['last_geometry'] = geometry()
        report['open_cpu_one_core_percent'] = cpu(pid)
        probe.close()
        report['hidden_cpu_one_core_percent'] = cpu(pid)
        report['passed'] = (report['app_pid_stable'] and report['open_cpu_one_core_percent'] < 25
                            and report['hidden_cpu_one_core_percent'] < 10)
        assert report['passed'], 'UI did not settle after transitions and repeated opens'
        report['stage'] = 'complete'
    finally:
        probe.close()
        (state/'transition-burst.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
