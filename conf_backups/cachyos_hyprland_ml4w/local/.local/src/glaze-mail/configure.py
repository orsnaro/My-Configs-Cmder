#!/usr/bin/env python3
"""Generate separate one-mailbox online evaluation configs, never old drafts."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import os
import shlex
import sys


CONFIG_DIRECTORY = Path.home() / ".config/glaze-mail/eval"
PREVIEW_PYTHON = Path.home() / '.local/share/glaze-mail/preview-venv/bin/python'


def _command(*paths: Path, prefix: tuple[str, ...] = (), suffix: tuple[str, ...] = ()) -> str:
    if any(not path.is_absolute() or any(c in str(path) for c in "\r\n\x00") for path in paths):
        raise ValueError("Commands require single-line absolute paths")
    return shlex.join([*prefix, *(str(path) for path in paths), *suffix])


def render_accounts(helper_python: Path, oauth_script: Path) -> str:
    command = _command(helper_python, oauth_script, prefix=("/usr/bin/timeout", "30s"), suffix=("token",))
    return (
        "[Central Gmail - online evaluation]\n"
        "source = imaps+xoauth2://omar.rashad.dev%40gmail.com@imap.gmail.com:993\n"
        f"source-cred-cmd = {command}\n"
        "from = omar.rashad.dev@gmail.com\n"
        "default = INBOX\ncache-headers = true\ncheck-mail = 5m\n"
        "outgoing = smtps+xoauth2://omar.rashad.dev%40gmail.com@smtp.gmail.com:465\n"
        f"outgoing-cred-cmd = {command}\n"
    )


def render_aerc(hook_python: Path, hook_script: Path) -> str:
    command = _command(hook_python, hook_script)
    preview = _command(PREVIEW_PYTHON, Path(__file__).resolve().parent / 'preview.py')
    return (
        "[ui]\nmouse-enabled = true\nnew-message-bell = false\n"
        "index-columns = flags:4,name<20%,labels<20%,subject,date>=\n"
        'column-labels = {{.Labels | join ", "}}\n'
        'column-separator = " │ "\n'
        "styleset-name = glaze\n"
        f"stylesets-dirs = {CONFIG_DIRECTORY/'stylesets'}\n"
        f"\n[hooks]\nmail-received = {command}\n"
        "\n[viewer]\n"
        "alternatives = text/html,text/plain\nhtml-inline-images = true\n"
        f"pager = /usr/bin/less -Rc --lesskey-src={CONFIG_DIRECTORY/'lesskey'}\n"
        "\n[compose]\neditor = /usr/bin/nano\n"
        "\n[openers]\ntext/plain = /usr/bin/gnome-text-editor --standalone\n"
        f"text/html = {preview} open-html --aerc-export\n"
        "\n[filters]\ntext/plain = /usr/lib/aerc/filters/colorize\n"
        f"text/html = {preview} text\n"
    )


def write_new_config(directory: Path, files: Mapping[str, str]) -> None:
    if set(files) != {"aerc.conf", "accounts.conf"}:
        raise ValueError("Only the two evaluation config filenames are allowed")
    for protected in (Path.home()/".config/aerc", Path.home()/".config/gcal"):
        if directory.resolve().is_relative_to(protected.resolve()):
            raise ValueError("Existing aerc/calendar paths cannot be used for evaluation output")
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise ValueError("Symlinked configuration directories are not supported")
    # Preflight every file before creating any, preserving existing user work.
    for name, content in files.items():
        target = directory/name
        if target.is_symlink():
            raise ValueError("Symlinked config files are not supported")
        if target.exists() and (not target.is_file() or target.read_text() != content):
            raise FileExistsError("Existing evaluation config differs; refusing overwrite")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    for name, content in files.items():
        target = directory/name
        if target.exists():
            target.chmod(0o600)
            continue
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())


def main() -> int:
    source = Path(__file__).resolve().parent
    python = Path.home()/".config/gcal/.venv/bin/python"
    try:
        write_new_config(CONFIG_DIRECTORY, {
            "accounts.conf": render_accounts(python, source/"oauth.py"),
            "aerc.conf": render_aerc(python, source/"toast.py"),
        })
        print(f"One-account evaluation configuration saved to {CONFIG_DIRECTORY}")
        return 0
    except (OSError, ValueError):
        print("Evaluation configuration was not written; check existing files/paths.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
