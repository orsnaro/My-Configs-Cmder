#!/usr/bin/env bash
# Restore this curated Pleamar overlay, never the legacy ML4W desktop.
# Preview is the default. --apply backs up first; it does not activate/unload anything.
set -euo pipefail

usage() {
    echo "Usage: bash $0 [--dry-run | --apply]"
    echo "No argument previews only. --apply verifies, backs up, then merges into HOME."
    echo "No packages, system patches, service changes, or compositor reloads are run."
    echo "For activation/unload, read RESTORE-CURRENT.md and RESTORE.md."
}

mode=--dry-run
if (( $# > 1 )); then usage >&2; exit 2; fi
if (( $# == 1 )); then
    case "$1" in
        --dry-run|--apply) mode=$1 ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
fi

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
: "${HOME:?HOME must name the home to restore}"
for command in python3 rsync cp; do
    command -v "$command" >/dev/null || { echo "Required command missing: $command" >&2; exit 1; }
done

dir_sources=(config/hypr config/kitty config/fish config/ohmyposh config/ml4w/settings source/vitreus data)
dir_destinations=(.config/hypr .config/kitty .config/fish .config/ohmyposh .config/ml4w/settings .config/pleamar/shells/vitreus .local/share/pleamar/vitreus)
file_sources=(systemd/pleamar.service bin/pleamar-start)
file_destinations=(.config/systemd/user/pleamar.service .local/bin/pleamar-start)
helper_names=()
helper_destinations=()
for source in "${dir_sources[@]}"; do
    [[ -d "$root/$source" ]] || { echo "Missing snapshot directory: $source" >&2; exit 1; }
done
for source in "${file_sources[@]}"; do
    [[ -f "$root/$source" ]] || { echo "Missing snapshot file: $source" >&2; exit 1; }
done
for helper in "$root/source/vitreus/bin/"*; do
    [[ -f "$helper" && -x "$helper" ]] || continue
    name=${helper##*/}
    helper_names+=("$name")
    helper_destinations+=(".local/bin/$name")
done

# Validate all payloads, relative aliases, and destination boundaries before
# creating even a backup directory. Do not silently copy unrecorded extra files.
python3 -B - "$root" "$HOME" "${dir_destinations[@]}" .local/state/pleamar-restore -- "${file_destinations[@]}" "${helper_destinations[@]}" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
home = Path(sys.argv[2]).resolve()
separator = sys.argv.index('--', 3)
try:
    manifest = json.loads((root / 'manifest.json').read_text())
    recorded: set[str] = set()
    for entry in manifest['files']:
        name: str = entry['path']
        path = root / name
        if name in recorded or not path.resolve().is_relative_to(root):
            raise ValueError(f'manifest path is duplicated or escapes the snapshot: {name}')
        recorded.add(name)
        if entry['kind'] == 'symlink':
            if not path.is_symlink() or os.readlink(path) != entry['target'] or Path(entry['target']).is_absolute():
                raise ValueError(f'manifest symlink mismatch: {name}')
        elif entry['kind'] != 'file' or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'manifest content mismatch: {name}')
        elif path.stat().st_size != entry['size'] or ('0755' if path.stat().st_mode & 0o100 else '0644') != entry['mode']:
            raise ValueError(f'manifest size/mode mismatch: {name}')
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob('*')
        if (path.is_file() or path.is_symlink()) and path != root / 'manifest.json'
        and not {'.git', '__pycache__'}.intersection(path.relative_to(root).parts)
        and path.suffix != '.pyc'
    }
    if recorded != actual:
        raise ValueError('manifest inventory does not match the snapshot payload')
    for relative in sys.argv[3:separator] + sys.argv[separator + 1:]:
        path = home / relative
        if not path.resolve().is_relative_to(home):
            raise ValueError(f'destination escapes HOME: {relative}')
    for relative in sys.argv[3:separator]:
        path = home / relative
        if (path.exists() or path.is_symlink()) and not path.is_dir():
            raise ValueError(f'destination is not an existing directory: {relative}')
    for relative in sys.argv[separator + 1:]:
        if (home / relative).is_dir():
            raise ValueError(f'file destination is a directory: {relative}')
    checkpoint = (home / '.local/state/pleamar-restore').resolve()
    for relative in sys.argv[3:separator - 1]:
        destination = (home / relative).resolve()
        if checkpoint.is_relative_to(destination) or destination.is_relative_to(checkpoint):
            raise ValueError(f'backup location overlaps a restored directory: {relative}')
except (OSError, ValueError, KeyError, RuntimeError) as error:
    raise SystemExit(f'Restore preflight/manifest verification failed: {error}')
print(f'Verified manifest: {len(recorded)} payload entries.')
PY

if [[ "$mode" == --dry-run ]]; then
    echo "DRY-RUN: no files or services will be changed. Planned merges:"
    for index in "${!dir_sources[@]}"; do
        printf '  %s/ -> %s/%s/\n' "${dir_sources[index]}" "$HOME" "${dir_destinations[index]}"
        if [[ -d "$HOME/${dir_destinations[index]}" ]]; then
            rsync -ain --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -- \
                "$root/${dir_sources[index]}/" "$HOME/${dir_destinations[index]}/"
        fi
    done
    for index in "${!file_sources[@]}"; do
        printf '  %s -> %s/%s\n' "${file_sources[index]}" "$HOME" "${file_destinations[index]}"
    done
    for name in "${helper_names[@]}"; do
        printf '  helper link: %s/.local/bin/%s\n' "$HOME" "$name"
    done
    echo "Use --apply only after reviewing RESTORE-CURRENT.md."
    exit 0
fi

# Preserve both original symlink structure and resolved bytes before the first
# configuration write. The enclosing checkpoint is owner-private.
umask 077
backup="$HOME/.local/state/pleamar-restore/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p -- "$(dirname -- "$backup")"
mkdir -m 700 -- "$backup"
for relative in "${dir_destinations[@]}" "${file_destinations[@]}" "${helper_destinations[@]}"; do
    destination="$HOME/$relative"
    if [[ -e "$destination" || -L "$destination" ]]; then
        mkdir -p -- "$backup/original/$(dirname -- "$relative")" "$backup/payload/$(dirname -- "$relative")"
        cp -a -- "$destination" "$backup/original/$relative"
        if [[ -e "$destination" ]]; then cp -aL -- "$destination" "$backup/payload/$relative"; fi
    else
        printf '%s\n' "$relative" >> "$backup/previously-absent.txt"
    fi
done
printf 'BACKUP=%s\n' "$backup"

for index in "${!dir_sources[@]}"; do
    destination="$HOME/${dir_destinations[index]}"
    mkdir -p -- "$destination"
    # Trailing destination slash preserves an existing ML4W root-directory link.
    # No --delete: unrelated settings and private runtime history stay untouched.
    rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -- \
        "$root/${dir_sources[index]}/" "$destination/"
done
for index in "${!file_sources[@]}"; do
    destination="$HOME/${file_destinations[index]}"
    mkdir -p -- "$(dirname -- "$destination")"
    cp -a --remove-destination -- "$root/${file_sources[index]}" "$destination"
done
for name in "${helper_names[@]}"; do
    ln -sfn -- "$HOME/.config/pleamar/shells/vitreus/bin/$name" "$HOME/.local/bin/$name"
done
echo "Restored files only; no desktop process was started, stopped, or reloaded."
echo "Read RESTORE-CURRENT.md before activation, or RESTORE.md for the legacy rollback."
