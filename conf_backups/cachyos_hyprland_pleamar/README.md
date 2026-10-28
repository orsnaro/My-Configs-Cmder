# Current Pleamar / Vitreus backup — 2026-10-28

Repository: `/shared_across_des/repos/My-Configs-Cmder`.

Pleamar **0.4.31**, its current working-tree source (including local changes),
Hyprland integration and safe persistent settings have been refreshed here.
The exact runtime, all scene settings, notes, pairing/integration state,
wallpapers and relevant QS/ML4W configuration are also preserved in a verified
**owner-private local snapshot** under `../.private/`.

No individual Pleamar widgets were disabled. Installation changed files only;
it did not activate a switch, stop/restart a process, or perform a lock/unlock.

## Two application-launcher entries

- **Switch to QS** — closes Pleamar's managed shell, every scene and keeper;
  starts the existing QS main/secondary status bars, dock, Walker/Elephant,
  SwayNC and its authentication agent.
- **Switch to Pleamar** — closes QS/docks/Walker/Elephant and the QS-specific
  background loop; starts the full saved Pleamar setup, including its lock
  scene and configured widgets.

Both remember the selected stack for the next Hyprland login. Repeated clicks
do not duplicate a healthy stack. Normal switching preserves installed
preferences; it does **not** overwrite newer settings from an old snapshot.
Unrelated applications, mounts, audio/network services and shared desktop
backends are not shut down. Switching while locked is refused.

The launcher scripts are in the repository root:

```bash
tools/switch-to-qs.sh
tools/switch-to-pleamar.sh
```

Use the application launcher or an external terminal, not a terminal embedded
in the stack being stopped; unsafe managed-service contexts are refused.

Theme/wallpaper/lazy-start hooks are mode-gated so they cannot silently restart
the inactive stack. An already-running GTK theme listener is refreshed only
when a switch is actually requested, to replace its old in-memory code. The
current desktop is otherwise left running. Logs: `~/.local/state/desktop-stack/operations.log`.

The launchers have been installed on the current machine. To reinstall links,
launcher files and guards from the **repository root**:

```bash
python3 tools/install_desktop_stack.py --dry-run
python3 tools/install_desktop_stack.py --apply
```

This installer backs up affected files privately, preserves config-root
symlinks, and does not run either desktop stack or reload services.

## Exact local recovery

From the repository root:

```bash
tools/recover-pleamar.sh             # verify and preview only
tools/recover-pleamar.sh --apply     # private pre-write checkpoint, then files
```

The current snapshot is selected by `conf_backups/.private/pleamar-current.json`.
Older snapshots and the previous curated export are retained. The recovery
tool reuses `tools/pleamar_migration/` verification/restore code; it does not
download/install packages or start/stop services. Prefer recovery from a TTY
with the graphical session logged out, so settings writers cannot race it.
Then log in or use **Switch to Pleamar** to activate the recovered setup.

**Keep `conf_backups/.private/` when copying this repository as a backup. It is
Git-ignored and contains credentials/pairing keys; it is not in commits and
must not be published.** This is local recovery for the existing account and
installed CachyOS/ML4W base, not a portable operating-system image. Re-creatable
Python environments, build caches and source Git metadata are excluded.

## Public curated overlay

`RESTORE.sh` remains dry-run-first and **file-only**:

```bash
bash RESTORE.sh --dry-run
bash RESTORE.sh --apply
```

It verifies the entire manifest, checkpoints original bytes/link metadata,
then merges without deleting unrelated data. After a public-overlay restore,
run the repository-root installer above to recreate the coordinator links and
the two app entries before activating the desktop.

| Export | Live destination |
| --- | --- |
| `source/vitreus/` | `~/.config/pleamar/shells/vitreus/` |
| `config/hypr/` | `~/.config/hypr/` |
| selected `config/ml4w/` files | `~/.config/ml4w/` |
| safe `data/` subset | `~/.local/share/pleamar/vitreus/` |
| `systemd/pleamar.service` | `~/.config/systemd/user/pleamar.service` |
| `bin/pleamar-start` | `~/.local/bin/pleamar-start` |
| retained `config/kitty`, `fish`, `ohmyposh` | corresponding `~/.config/` trees |

The public Kitty/Fish/Oh My Posh payload is retained from the October 25–26 export;
current terminal/theming state is additionally preserved in the private snapshot,
without publishing unrelated terminal edits. Full private
scene state is not limited to the public `data/` subset: desktop notes, other
widgets, news/weather and TV pairing state are in the protected snapshot.

No private credentials, notes/history, weather location, pairing keys, logs or
compiled binaries are included in the public payload. The exact Pleamar binary
is in the private snapshot; its hash/version are in `versions/pleamar.txt`.
The base desktop's installed packages/fonts/icon themes remain prerequisites.

## Verification and limitations

See [CHECKS.md](CHECKS.md). The real private snapshot was restored into a
temporary home: **1099 actions**, with **zero remaining byte/mode/alias
differences**. Runtime executability, private key permissions and both launcher
files were checked. The public overlay also passed preview and actual apply in
a temporary home.

Tests cover both switch directions, repeated/concurrent requests, locked-session
refusal, failure rollback, hidden restart guards and shared-process preservation.
**A real live switch, reboot/login cycle and lock/unlock were not performed.**
One pre-existing focused-GUI Kitty test remains skipped. Independent review was
unavailable after the configured free-model quota was reached; review continued
inline without model escalation.

`RESTORE.md` and `HISTORY-2026-10-20.md` describe the older migration; do not use
upstream `install.sh --stop/--uninstall` or overwrite the entire desktop from an
old profile as a substitute for these switchers.
