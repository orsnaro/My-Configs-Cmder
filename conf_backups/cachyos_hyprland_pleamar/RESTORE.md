# Restore guide — back to the pre-Pleamar ML4W / Quickshell desktop

> **Historical, machine-local rollback guide (2026-10-19).** To restore/load the
> current October 25 Pleamar snapshot, use **[RESTORE-CURRENT.md](RESTORE-CURRENT.md)**
> and its dry-run-by-default `RESTORE.sh`, not this procedure. The private rollback
> payload, metadata companion, and `tools/pleamar_migration/` referenced below are
> local prerequisites and are **not included in this snapshot's PR**. Confirm that
> all exist and review current changes before attempting the rollback. Upstream
> `install.sh --stop`/`--uninstall` does not reverse this managed service cutover.

For **this machine and user** (`narol`, home `/home/narol`). It reverts the
permanent Pleamar/Vitreus desktop (installed 2026-10-19) to the ML4W/Quickshell
desktop that ran before it. Nothing is uninstalled; files are restored and the
session is switched back.

**The rollback pair this guide uses** (outside this folder):

| Part | Path |
| --- | --- |
| Private payload (302 MB, owner-only) | `~/.local/state/pleamar-migration/pre-pleamar-20261019-172818/private` |
| Public metadata companion | `/shared_across_des/repos/My-Configs-Cmder/conf_backups/cachyos_hyprland_pre_pleamar_20261019-172818` |

**Hard rules:** never run `hands_on.py revert`; never run
`cachyos_hyprland_ml4w/BACKUP.sh`; dry-run always before `--apply`.

## 0. What the restore actually changes

The snapshot restore rewrites files whose bytes or modes differ, and can
recreate missing recorded paths. The 2026-10-19 19:50 dry-run planned **19 writes**;
the current list may differ:

- **2 cutover edits** — `.config/hypr/hyprland.lua` and
  `.config/hypr/conf/autostart.lua`. These two *are* the desktop switch.
- **14 ML4W/Quickshell color files** (`colors.conf`, `colors.lua`, `colors.css`
  for swaync/waybar/walker, `colors.rasi`, `colors.json` ×3, `primary`,
  `secondary`, `onprimary`, `onsurface`, `Appearance.colors.qml`) —
  regenerated since the snapshot by the ML4W wallpaper automation.
  ML4W regenerates these again from your wallpaper after any re-theme.
- **3 trial-state JSONs** under `.local/state/pleamar-trial/20261018-203156/…`
  (stale trial data; harmless either way).

Everything else matched in that dry-run. With this journal, the restore
**never deletes** files that the cutover created (none are recorded as created)
and never touches paths outside the snapshot.

## 1. Review changes before authorizing replacement

`restore.py` refuses to overwrite a path whose live bytes changed since the
snapshot unless a journal records that exact state. No original deployment
journal was found. `authorize.py` can record current states for replacement,
but **it cannot establish who changed those files or whether they are safe to
overwrite**. Its `reviewed_paths` field is a candidate list, not proof of human
review. Start with this read-only preview:

```bash
cd /shared_across_des/repos/My-Configs-Cmder

python3 -m tools.pleamar_migration.authorize \
  --snapshot-root ~/.local/state/pleamar-migration/pre-pleamar-20261019-172818/private \
  --companion-root conf_backups/cachyos_hyprland_pre_pleamar_20261019-172818 \
  --home "$HOME" \
  --out ~/.local/state/pleamar-migration/restore-journal.json
```

- **Inspect every candidate and compare it with its snapshot payload.** Back up
  current bytes and symlink targets in owner-private storage before replacing
  anything. Preserve any changes you want to retain; the 19-path appendix is
  historical, not approval to overwrite new edits.
- Only after explicitly approving all replacements, repeat the preview command
  with `--write`. This writes a 0600 journal; it does not restore the desktop.
  Check the resulting path list against what you just approved. There is no
  per-path skip option: use selective manual recovery if any replacement is
  unwanted.
- **Do not automatically regenerate the journal to clear a conflict.** Later
  edits are a safety stop: inspect and back them up, then make a fresh decision.

## 2. Dry-run the restore

```bash
python3 -m tools.pleamar_migration.restore \
  --snapshot-root ~/.local/state/pleamar-migration/pre-pleamar-20261019-172818/private \
  --companion-root conf_backups/cachyos_hyprland_pre_pleamar_20261019-172818 \
  --home "$HOME" \
  --journal ~/.local/state/pleamar-migration/restore-journal.json
```

Expected: JSON with `"applied": false`, the actions you reviewed, and exit 0.
The recorded 19:50 run had 19 `write` actions; that count is not a future guarantee.

- `Restore blocked: destination changed since snapshot: …` — unapproved drift;
  inspect/back up the changed file and review step 1 again. Do not simply bypass it.
- `Restore blocked: <anything else>` — a path needs a manual decision (for
  example a file that must be a directory); resolve that path by hand first.

## 3. Apply

Same command as step 2 with `--apply` at the end. The tool re-checks every
precondition while writing and stops on any mismatch.

## 4. Switch the live session back

```bash
systemctl --user stop pleamar.service      # the Pleamar bar goes away
systemctl --user unmask swaync.service     # undo the cutover's persistent mask
hyprctl reload                             # restored hyprland.lua + ML4W binds
```

Then **log out and back in** (or reboot): the restored `autostart.lua` starts
the ML4W stack again — `ml4w-autostart` (Quickshell), `waybar/launch.sh`,
`swaync`, `elephant` + `walker --gapplication-service`, hypridle, hyprsunset,
cliphist watcher.

Same session, without re-login (best effort):

```bash
~/.config/ml4w/scripts/ml4w-autostart        # Quickshell, dock, wallpaper
~/.config/waybar/launch.sh                   # waybar
swaync &                                     # notifications
elephant &                                  # launcher backend
walker --gapplication-service &              # launcher UI
```

## 5. Verify

```bash
systemctl --user status pleamar.service        # inactive (dead)
systemctl --user is-enabled swaync.service     # no longer "masked"
for p in qs waybar swaync elephant walker; do
  pgrep -x "$p" >/dev/null && echo "$p: running" || echo "$p: not running"
done
```

Visual: ML4W bar + dock back; `Super+R` opens Walker; notifications come from
swaync; `hyprctl reload` reports no errors. `Super+B` (Brave) and `Super+Space`
(keyboard layout) were preserved by the snapshot and keep working.

If colors look mismatched to the wallpaper, ML4W regenerates them from it:

```bash
~/.config/ml4w/scripts/ml4w-wallpaper "$(cat ~/.cache/ml4w/hyprland-dotfiles/current_wallpaper)"
```

## 6. Manual fallback (no tools)

The desktop startup/bind switch is two files; this is not a complete snapshot
restore. Inspect differences and back up both current files (including their
resolved symlink targets) before overwriting them:

```bash
systemctl --user stop pleamar.service
systemctl --user unmask swaync.service
P=~/.local/state/pleamar-migration/pre-pleamar-20261019-172818/private/payload
cp "$P/.config/hypr/hyprland.lua" ~/.config/hypr/hyprland.lua
cp "$P/.config/hypr/conf/autostart.lua" ~/.config/hypr/conf/autostart.lua
hyprctl reload
# then log out and back in
```

## 7. What stays behind (optional cleanup)

Pleamar remains installed and inert: `~/.config/pleamar/`,
`~/.local/bin/pleamar*`, `~/.config/systemd/user/pleamar.service` (static, not
enabled, only started by the now-restored-away autostart hook),
`~/.config/hypr/hypr_vitreus.lua` (nothing requires it anymore) and
`~/.local/share/pleamar/`. Keep them if you may try Pleamar again — it is the
same pinned 0.4.18 build; remove later only if you are sure.

Keep the rollback pair directories intact — this guide needs them.
`conf_backups/cachyos_hyprland_ml4w/` is unrelated dirty user work: leave it
untouched.

## 8. How this guide was verified (2026-10-19)

- Migration suite (snapshot + restore + stage + authorize): **48/48 OK**
  (`.superpowers/sdd/2026-10-19-permanent-pleamar-desktop/r4-suite.log`).
- Real pair: authorize reviewed exactly the 19 paths
  (`…/r4-authorize.log`); restore dry-run with the journal: exit 0, 19
  `write` actions, no conflicts (`…/r4-restore-dry-run.json`).
- The full `--apply` was **not** executed; the live revert remains your call.

## Appendix — the 19 reviewed paths

```
.mydotfiles/com.ml4w.dotfiles.stable/.config/hypr/colors.conf
.mydotfiles/com.ml4w.dotfiles.stable/.config/hypr/colors.lua
.mydotfiles/com.ml4w.dotfiles.stable/.config/hypr/hyprland.lua
.mydotfiles/com.ml4w.dotfiles.stable/.config/hypr/conf/autostart.lua
.mydotfiles/com.ml4w.dotfiles.stable/.config/ml4w/colors/colors.json
.mydotfiles/com.ml4w.dotfiles.stable/.config/ml4w/colors/onprimary
.mydotfiles/com.ml4w.dotfiles.stable/.config/ml4w/colors/onsurface
.mydotfiles/com.ml4w.dotfiles.stable/.config/ml4w/colors/primary
.mydotfiles/com.ml4w.dotfiles.stable/.config/ml4w/colors/secondary
.mydotfiles/com.ml4w.dotfiles.stable/.config/rofi/colors.rasi
.mydotfiles/com.ml4w.dotfiles.stable/.config/swaync/colors.css
.mydotfiles/com.ml4w.dotfiles.stable/.config/waybar/colors.css
.config/ml4w-dock/colors.json
.config/walker/colors.css
.local/share/ml4w-dotfiles-settings/colors/colors.json
.local/share/quickshell-overview/common/Appearance.colors.qml
.local/state/pleamar-trial/20261018-203156/hands-on/xdg/data/pleamar/vitreus/notification-history.json
.local/state/pleamar-trial/20261018-203156/hands-on/xdg/data/pleamar/vitreus/notification-rules.json
.local/state/pleamar-trial/20261018-203156/hands-on/xdg/data/pleamar/vitreus/wx.json
```
