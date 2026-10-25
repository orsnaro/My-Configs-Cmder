# Restore the current Pleamar configuration overlay

This procedure restores **files**, not packages or a full desktop image. The
existing CachyOS/ML4W base, local command helpers, fonts, wallpapers, Pleamar
0.4.18, Fish, and Oh My Posh must already be installed. See `versions/` and
`README.md`. No runtime-changing command was executed to verify this guide.

## 1. Inspect first

Run from this export directory:

```bash
bash RESTORE.sh --dry-run
```

The default without arguments is also a dry-run. It verifies the manifest's full
inventory, hashes, sizes, modes, safe source aliases, and destination boundaries,
then previews merges and helper links. It does not even create a backup directory.
Unknown/conflicting options are rejected. A mismatch is a stop: do not bypass
verification without investigating it.
Public files record Git-checkout-portable 0644/0755 permissions. Validation checks
the executable bit Git actually stores, accepting a tighter checkout umask; the
merge preserves that checkout's file permissions. Original live modes are retained
as audit metadata in the manifest's `source_mappings`; they are not reapplied over
unrelated private data.

This snapshot assumes the usual `$HOME/.config` and `$HOME/.local` layout; it is
not a migration to alternate XDG roots. Existing config-directory symlinks may
point elsewhere **inside HOME** and are preserved. Destinations resolving outside
HOME, wrong file/directory types, or a backup directory overlapping restored data
are rejected. Review the machine-specific monitor names, GPU wrapper, paths,
slideshow setting, and command dependencies before continuing.

## 2. Back up and merge

Close editors and save your work. Prefer applying from a TTY while the graphical
session is logged out, so background settings writers cannot race the restore.
Do not run as another user or with sudo.

```bash
bash RESTORE.sh --apply
```

Before modifying configuration, it creates an owner-private checkpoint at:

```
~/.local/state/pleamar-restore/<UTC timestamp>-<PID>/
  original/                original files/directory links, without dereferencing
  payload/                 resolved original content, including linked config roots
  previously-absent.txt    destination roots/helper names absent before this restore
```

If creating/copying that backup fails, the script exits before any config write.
Keep the printed `BACKUP=` path. After backup it merges the selected config and
settings directories, copies the wrapper/unit, and recreates executable scene
helper links in `~/.local/bin/`. It does **not** use `--delete`, copy private
histories from this repo, chmod unrelated files, install packages, or patch Kitty.

A later I/O failure can leave a partial restore: this is not a transaction or an
automatic rollback engine. The full pre-write checkpoint remains available for
manual recovery. Inspect original links and resolved payloads together before
recovering files, and review `previously-absent.txt` rather than deleting anything
automatically. Private checkpoints may contain private existing runtime data;
never commit them to this public repository.

## 3. Activate only when ready

The restore script never calls `systemctl`, `hyprctl`, `pkill`, package managers,
upstream installers, or network downloads. It does not enable the static unit,
stop competing shells, or change the persistent SwayNC mask.

For the existing machine, the next Hyprland login runs the copied startup hook
and starts `pleamar.service`; the separate lock scene is started by that same
hook. Opening a new Fish/Kitty session loads the restored prompt/config.
After copying a unit, the user manager may first need an explicit reload. These
are **manual activation commands**, not part of `RESTORE.sh`:

```bash
systemctl --user daemon-reload
# Only after checking competing shell/notification ownership and saving work:
systemctl --user restart pleamar.service
hyprctl reload
```

Reloading Hyprland does not rerun its startup hook; a new login is the normal way
to start all separate startup scenes. Never stop a lock scene during an active
lock. This refresh did not exercise live activation, display-Keep, or lock/unlock.

## 4. Unload / return to ML4W

For a temporary stop, `systemctl --user stop pleamar.service` stops the managed
main shell, **not** the independent lock/widget scenes or next-login autostart.
It does not restore the old desktop. Do not use upstream `install.sh --stop`:
that command was built for an unmanaged trial, not this systemd cutover.

For a permanent return to the pre-Pleamar desktop, read `RESTORE.md` and inspect
its exact local rollback pair and migration tools first. They are not shipped in
this PR. The historical guide requires an authorization preview/journal before
changed live files can be replaced. Neither upstream `--uninstall` nor the legacy
ML4W `RESTORE.sh` is a safe substitute: they do not reverse this profile's managed
service/autostart/notification ownership completely.
