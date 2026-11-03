"""Short-lived safe HTML preview commands; cleanup needs only the standard library."""
from __future__ import annotations

from pathlib import Path
import argparse
import os
import subprocess
import sys

from preview_files import (MAX_BYTES, PreviewContext, cleanup, context_from_environment,
                           create_preview, read_aerc_export, discard_export)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError('Invalid preview command')


def current_cgroup() -> str:
    return Path('/proc/self/cgroup').read_text()


def require_active_context(context: PreviewContext) -> None:
    result = subprocess.run(['/usr/bin/systemctl', '--user', 'show', context.unit_name,
                             '--property=InvocationID,ActiveState,ControlGroup,ExecStopPost'],
                            capture_output=True, text=True, check=True, timeout=5)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    group = values.get('ControlGroup', '')
    hook = f'argv[]={sys.executable} {Path(__file__).resolve()} cleanup ;'
    if (values.get('InvocationID') != context.invocation_id or values.get('ActiveState') != 'active' or
            not group.startswith('/') or group == '/' or '..' in Path(group).parts or
            hook not in values.get('ExecStopPost', '')):
        raise ValueError('Reopen mail to activate private preview cleanup')
    own_groups = [line.split(':', 2)[2] for line in current_cgroup().splitlines() if line.startswith('0::')]
    if not any(own == group or own.startswith(group + '/') for own in own_groups):
        raise ValueError('Preview must belong to the active mail service')


def notify_failure() -> None:
    try:
        subprocess.run(['/usr/bin/notify-send', '-a', 'aerc-mail', '-i', 'internet-mail', '-t', '6000',
                        'aerc Mail', 'Safe HTML preview unavailable. Reopen mail after setup, or check its private preview runtime.'],
                       capture_output=True, check=False, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def main(argv: list[str] | None = None) -> int:
    mode = ''
    try:
        parser = _Parser(description=__doc__)
        parser.add_argument('mode', choices=('text', 'open-html', 'cleanup'))
        parser.add_argument('--aerc-export', type=Path)
        args = parser.parse_args(argv)
        mode = args.mode
        if mode != 'open-html' and args.aerc_export is not None:
            raise ValueError('Unexpected export argument')
        if mode == 'text':
            from preview_html import html_to_text
            data = sys.stdin.buffer.read(MAX_BYTES + 1)
            sys.stdout.write(html_to_text(data))
        elif mode == 'cleanup':
            cleanup(context_from_environment(os.environ))
        else:
            if args.aerc_export is None:
                raise ValueError('Native export required')
            context = context_from_environment(os.environ)
            require_active_context(context)
            export = read_aerc_export(args.aerc_export)
            try:
                page = create_preview(export.data, context).with_name('images.html')
                from preview_desktop import launch_preview
                launch_preview(page, context)
            finally:
                discard_export(export)
        return 0
    except Exception:
        print('Safe HTML preview unavailable; check setup and reopen mail.', file=sys.stderr)
        if mode == 'open-html':
            notify_failure()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
