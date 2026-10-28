# Pleamar recovery and mutually exclusive desktop stacks

## Intent and agreed behavior

Preserve the entire current Pleamar/Vitreus configuration in the existing
`/shared_across_des/repos/My-Configs-Cmder` repository before returning to
Quickshell. Reuse the existing backup/restore machinery. Do not selectively
disable Pleamar widgets, change their settings, or switch the live desktop
during installation/verification.

Provide exactly two application-launcher entries backed by executable shell
scripts in `tools/`:

- **Switch to QS**: stop all Pleamar scenes, their restart keepers and managed
  service; start the existing Quickshell main/secondary bars, docks and
  Walker/Elephant stack with its notification/authentication integration.
- **Switch to Pleamar**: stop all QS instances/docks, Walker/Elephant and their
  restart activity; start the saved full Pleamar setup, including its native
  lock scene and configured widgets.

The user selected **Remember selected stack**: only the last successfully
selected stack starts on the next Hyprland login. Repeated clicks are
idempotent, not on/off toggles. Initial installation preserves Pleamar as the
selected mode and does not activate either launcher automatically.

## Approach and alternatives

Use one shared, serialized coordinator and two thin shell entrypoints.
Mode-gate existing login/restart/keyboard hooks rather than replacing the
whole desktop configuration. This keeps the existing settings and avoids
divergent stop/start logic.

Rejected: copying a complete historical Hyprland profile on each click would
overwrite newer user configuration. Killing processes alone would allow
startup hooks, services and theme listeners to bring the inactive stack back.

## Backup and recovery

Keep the curated export at `conf_backups/cachyos_hyprland_pleamar/` and its
manifest-verified, dry-run-first, file-only `RESTORE.sh` contract. Refresh it
from the current working-tree bytes, including uncommitted/new source files,
current Hyprland integration and current safe persistent settings. Do not
publish credentials, private notes/history, notification contents or pairing
keys.

Reuse `tools/pleamar_migration/snapshot.py` for a complementary owner-private
snapshot under Git-ignored `conf_backups/.private/`. Include all scene settings,
private integrations, helper links and resolved contents, the exact Pleamar
runtime and compiled helper, wallpapers and relevant ML4W configuration.
Preserve original file modes and link metadata. Exclude source Git metadata,
build caches and recreatable environments; document their prerequisites.
Keep the old curated export before refreshing it. Verify the snapshot and
compare selected payloads with their live sources.

Switching normally uses the installed settings; it must not restore an old
snapshot over newer preferences at every click. A documented recovery action
reuses the existing restore machinery, validates the backup first and creates
a private pre-write checkpoint before overwriting settings. Pleamar activation
then goes through the same coordinator, not a second service-switch path.
Missing/corrupt recovery prerequisites must fail visibly, not claim success.

## Integration boundaries

Use a small persisted mode file under the user's config directory. It must be
read consistently by Hyprland login, mode-specific keybindings, lock routing,
systemd activation and any identified theme/lazy-launch/restart hooks.
The mode affects only these desktop stacks: unrelated applications, mounts,
sync timers, Bluetooth/network daemons, audio, compositor and shared clipboard
services remain untouched.

Start and stop existing components through their existing entrypoints where
safe. Stop restart owners before their child processes. Match only the current
user's known stack processes; never use a broad `pkill -f` expression that can
kill the coordinator, terminals or unrelated applications. Stop/mask only
identified opposing stack services and unmask the selected stack's required
services. Do not blanket-disable systemd or XDG autostart.

Preserve shared theme/display state and keep Pleamar's saved files available
while QS runs. Route lock requests to the selected stack's locker. Never tear
down a running session lock: reject a switch while locked, and fail closed if
the native lock's state cannot be safely established.

## Failure handling

Preflight the selected stack's binaries/configuration before stopping the
running stack. Use a cross-process lock to serialize switch/login requests.
Use readiness/state checks and bounded waits rather than unconditional delays.
Do not report success or commit the remembered selection until startup is
verified. On activation failure, restore the previous selection and attempt to
restart its stack; report both the original failure and any rollback failure.
Keep an owner-private operation log for diagnosis. Duplicate activation must
not create extra bars, keepers, wallpaper loops or launchers.

## Packaging and verification

Install two `.desktop` entries under `~/.local/share/applications/` and local
command links to the repo scripts. Scripts must work independently of the
current working directory. Install/gate only the necessary live hooks, with
private pre-edit backups; do not run a live switch as part of installation.
Keep these tools/hooks represented in the refreshed backup.

Tests use fake commands and temporary homes: both switch directions, repeated
activation, remembered-mode login, lock rejection, missing dependencies,
startup failure/rollback, inactive-stack restart suppression and unrelated
process preservation. Restore tests cover byte/mode/link parity, private data
permissions, corrupt payload rejection and no service calls from the file-only
restore. Run existing relevant suites and distinguish fixture verification
from a real live switch/lock cycle. Do not claim live acceptance without it.

## Existing work and Git safety

Work on `fix/pleamar-backup-and-stack-switch`. Preserve all pre-existing dirty
ML4W backups, untracked migration tools/tests and historical checkpoint files.
Use fingerprints to verify unrelated content is unchanged. No automatic push.
