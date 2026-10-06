#!/usr/bin/env bash
set -euo pipefail
# Sysinfo contract: separate CPU + RAM pills, shared metrics panel.
app="$HOME/.config/quickshell/StatusbarApp"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -x "$HOME/.local/bin/hypr-sysinfo" ]] || fail "hypr-sysinfo script missing"
"$HOME/.local/bin/hypr-sysinfo" >/dev/null
[[ -f "$HOME/.cache/sysinfo.json" ]] || fail "sysinfo cache missing (run hypr-sysinfo)"
python3 -c "import json;d=json.load(open('$HOME/.cache/sysinfo.json'));assert all(k in d for k in ('cpu_pct','cpu_ghz','mem_pct','cores','load','uptime','top'))" \
    || fail "cache must carry cpu/mem/cores/load/uptime/top"
[[ -f "$app/CpuModule.qml" ]] || fail "CpuModule.qml missing"
[[ -f "$app/MemModule.qml" ]] || fail "MemModule.qml missing"
[[ -f "$app/SystemPanel.qml" ]] || fail "SystemPanel.qml missing"
need "$app/CpuModule.qml" "sysinfo.json" "CpuModule must read the sysinfo cache"
need "$app/MemModule.qml" "sysinfo.json" "MemModule must read the sysinfo cache"
need "$app/SystemPanel.qml" "per-core\\|cores" "SystemPanel must show per-core metrics"
need "$app/StatusbarWindow.qml" "cCpu" "StatusbarWindow must register cCpu"
need "$app/StatusbarWindow.qml" "cMem" "StatusbarWindow must register cMem"
python3 - "$app" <<'PY'
import json, pathlib, re, sys
app = pathlib.Path(sys.argv[1])
default = (app / 'StatusbarWindow.qml').read_text()
documented = (app / 'config.json').read_text()
for name, text in [('built-in', default), ('documented', documented)]:
    match = re.search(r'"right"\s*:\s*\[([^\]]+)\]', text)
    assert match, f'{name}: missing right-side module list'
    order = re.findall(r'"(\w+)"', match.group(1))
    assert order[:3] == ['cpu', 'mem', 'updates'], f'{name}: CPU/RAM should precede updates, got {order}'
    assert order[-3:] == ['volume', 'keyboard', 'power'], f'{name}: right must end volume,keyboard,power, got {order}'

data = json.loads((pathlib.Path.home() / '.cache/sysinfo.json').read_text())
assert isinstance(data['cpu_temp'], (int, float, type(None))), 'CPU temperature must be numeric or unavailable'
gpu = data['gpu']
assert gpu['name'] == 'AMD Radeon', f'expected discrete AMD GPU, got {gpu}'
assert isinstance(gpu['usage'], (int, float)) and 0 <= gpu['usage'] <= 100, gpu
assert isinstance(gpu['temp'], (int, float, type(None))), gpu
assert isinstance(gpu['vram_used_gb'], (int, float, type(None))), gpu
assert isinstance(gpu['vram_total_gb'], (int, float, type(None))), gpu

def sensor(name):
    for folder in pathlib.Path('/sys/class/hwmon').glob('hwmon*'):
        if (folder / 'name').read_text().strip() == name:
            return folder
    raise AssertionError(f'missing {name} sensor')

package = float((sensor('coretemp') / 'temp1_input').read_text()) / 1000
gpu_edge = float((sensor('amdgpu') / 'temp1_input').read_text()) / 1000
assert data['cpu_temp'] is not None and abs(data['cpu_temp'] - package) <= 10, (data['cpu_temp'], package)
assert gpu['temp'] is not None and abs(gpu['temp'] - gpu_edge) <= 10, (gpu['temp'], gpu_edge)
assert gpu['vram_used_gb'] is not None and gpu['vram_total_gb'] is not None and 0 <= gpu['vram_used_gb'] <= gpu['vram_total_gb'], gpu
PY
need "$app/SystemPanel.qml" 'GPU' "system panel must display GPU metrics"
printf 'PASS: sysinfo modules wired\n'
