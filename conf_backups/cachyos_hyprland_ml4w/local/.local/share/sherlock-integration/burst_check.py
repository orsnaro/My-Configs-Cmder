"""Real app-wrapper regression: repeated opens must not spin or shrink the UI."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='latest')
    args = parser.parse_args()
    assert args.label in ('red', 'green', 'latest')
    home = Path.home()
    state = home/'.local/state/sherlock-migration/20261102/meta-fix'
    subprocess.run(['systemctl', '--user', 'restart', 'sherlock.service'], check=True, timeout=30)
    pid = int(subprocess.check_output(['systemctl', '--user', 'show', 'sherlock.service', '-p', 'MainPID', '--value'], text=True))

    def ticks() -> int:
        fields = (Path('/proc')/str(pid)/'stat').read_text().split(') ', 1)[1].split()
        return int(fields[11])+int(fields[12])

    def cpu() -> float:
        start = time.monotonic()
        before = ticks()
        time.sleep(2)
        return round((ticks()-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-start)*100, 3)

    report: dict[str, object] = {'pid': pid, 'opens': 60}
    try:
        for _ in range(60):
            subprocess.run([str(home/'.config/hypr/scripts/launcher.sh')], check=True, timeout=8,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            time.sleep(.05)
        time.sleep(.8)
        data = json.loads(subprocess.check_output(['hyprctl', '-j', 'layers'], text=True))
        geometry = [{'monitor': name, **{key: row.get(key) for key in ('pid', 'w', 'h')}}
                    for name, monitor in data.items() for level in monitor['levels'].values()
                    for row in level if row['namespace'] == 'sherlock']
        report['geometry'] = geometry
        report['open_cpu_one_core_percent'] = cpu()
    finally:
        payload = b'"Close"'
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(2)
            connection.connect('/tmp/sherlock_daemon.sock')
            connection.sendall(len(payload).to_bytes(4, 'big')+payload)
        time.sleep(.3)
    report['hidden_cpu_one_core_percent'] = cpu()
    report['same_daemon_pid'] = pid == int(subprocess.check_output(['systemctl', '--user', 'show', 'sherlock.service', '-p', 'MainPID', '--value'], text=True))
    report['passed'] = (any(row['pid'] == pid and row['w'] == 900 and row['h'] == 593 for row in geometry)
                        and report['open_cpu_one_core_percent'] < 25
                        and report['hidden_cpu_one_core_percent'] < 10 and report['same_daemon_pid'])
    (state/f'burst-{args.label}.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    assert report['passed'], 'Repeated app opening regressed window geometry or left the UI spinning'


if __name__ == '__main__':
    main()
