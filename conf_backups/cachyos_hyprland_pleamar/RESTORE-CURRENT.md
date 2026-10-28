# Recover the current Pleamar setup

## Normal return from QS: one launcher action

Choose **Switch to Pleamar** in the application launcher. It stops the complete
QS/Walker/Elephant stack and activates the full saved Pleamar setup. Settings
remain installed while QS is active, so normal switching does not restore old
files over newer preferences. **Switch to QS** performs the reverse operation.
The last successfully selected stack is used at the next Hyprland login.

## Restore damaged/missing files from the exact local snapshot

From `/shared_across_des/repos/My-Configs-Cmder`:

```bash
tools/recover-pleamar.sh                    # verify/preview; no writes
tools/recover-pleamar.sh --apply            # checkpoint original bytes, restore
```

The Git-ignored pointer `conf_backups/.private/pleamar-current.json` selects the
verified private/public snapshot pair. An explicit `--snapshot <bundle>` can
select an older retained snapshot. `--home` is for deliberate alternate-home
recovery/fixtures; this machine's absolute paths and installed dependencies
must be reviewed before using it for another account.

Prefer a TTY with the graphical session logged out before `--apply`: running
applications can write settings during restoration. Corruption/missing
prerequisites fail before destination writes. Changed destination bytes are
captured in an owner-private checkpoint before replacement; a later failure
retains that checkpoint and prints its location. This is not an atomic
whole-desktop rollback transaction.

Recovery restores files, permissions and link metadata, **not running
processes**. After recovery, log in or choose **Switch to Pleamar**. Its normal
activation path reloads the user manager/configuration and applies the
selected stack's service policy. Never bypass the lock-state check by killing
lock processes manually.

The private snapshot includes the exact Pleamar runtime, compiled inhibitor,
all scene settings, wallpapers, private integrations and new switch hooks.
Build caches, source Git history and recreatable virtual environments are not
included. The existing OS/ML4W packages/fonts/icons remain prerequisites.

**The private snapshot is local-only and contains secrets. Keep the entire
`conf_backups/.private/` directory for exact recovery, but never publish it.**

## Curated public overlay only

From this export directory:

```bash
bash RESTORE.sh --dry-run                  # default; full manifest validation
bash RESTORE.sh --apply                    # private checkpoint, merge files only
```

The overlay assumes the installed base and Pleamar 0.4.31. It does not include
the binary or private notes/keys/history. It preserves config-root aliases
inside HOME and unrelated destination files; unsafe destinations are rejected.
It does not install packages, patch Kitty, alter services, or reload Hyprland.

Then, from the repository root, recreate the coordinator links/app entries:

```bash
python3 tools/install_desktop_stack.py --apply
```

The installer is also file-only, idempotent and pre-write-checkpointed. Choose
the desired launcher after reviewing the restored machine-specific settings.
Do not run the captured upstream installer/uninstaller or the legacy ML4W
restore script for this workflow.
