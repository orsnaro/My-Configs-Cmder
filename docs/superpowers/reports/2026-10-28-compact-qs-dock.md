# Compact QS dock — 2026-10-28

## Cause and applied change

The dock process and IPC were healthy, but the live config had
`dock.enabled=false`. DockLoader correctly left its window uninstantiated;
restarting would have preserved that saved disabled preference. No switcher or
production QML/script change was needed.

Applied only the five approved live values in
`~/.config/ml4w-dock/config.json`:

| Preference | Before | After |
| --- | ---: | ---: |
| dock.enabled | false | true |
| dock.iconSize | 22 | 20 |
| dock.spacing | 6 | 5 |
| pill.padding | 8 | 6 |
| dock.marginBottom | 11 | 6 |

Icons are approximately 9% smaller (whole-pixel sizing). The visible pill height
is 42px instead of 48px. Its reserved bottom strip, including the margin, is
**48px instead of the previous visible configuration's 59px**. The taller 202px
layer window includes transparent click-through space for shadows/menus; it
does not reserve that full height from application windows.

Six current pins and their order, launcher, DP-2 monitor, autohide=false,
colors, border/radius and all other live bytes are unchanged. Only the existing
`ml4w-dock reload` IPC was sent. Quickshell, the dock, Elephant, SwayNC and polkit
retain their original process identities; other monitors' reservations are
unchanged. One dock layer is present on DP-2.

## Verification

- The real DockSettings consumer, loaded in isolated offscreen QML, first
  failed on the old disabled preference. It now accepts all approved settings
  against both saved and live sources. No desktop window is created by this
  new fixture.
- Full root suites: **12 QS**, **39 desktop-stack**, **17 migration** tests
  passed. Existing dock preview contract passed. Existing isolated Qt gesture
  tests passed **22 gesture + 2 fresh-process persistence cases**, with no
  failures or skips. Their apps, settings and input targets are disposable
  fixtures, not the live dock's pins/applications.
- A concurrent RED test host initially appeared in the broad process baseline.
  That transient offscreen `qs` PID was excluded after inspection; all five
  actual persistent desktop PIDs/start times remain unchanged. No restart was
  performed to satisfy an assertion.
- All **27** original-checkout dirty/untracked fingerprints and **16** live
  source/config hashes are unchanged, including all dock QML and the TV helper.
  No TLS/Copilot, Code OSS, Pleamar, main-bar or launcher edits belong here.
- No clipboard contents, screenshots or real app activation/close/pin actions
  were used for acceptance. No reboot/login, desktop-switch roundtrip or user
  visual confirmation is claimed for this change.

## Backup and review

The exact live config is mirrored at
`conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/ml4w-dock/config.json` on
`fix/compact-qs-dock`. Its six pins intentionally reflect the current live
configuration rather than that committed historical file's four older pins.
The original checkout's unrelated dirty backup files were **not overwritten**.

The Git-ignored owner-private recovery snapshot was refreshed. It contains 1066
entries, seven cache/build exclusions and 938 protected payload files. Isolated
recovery applied **1100 actions with zero remaining differences**, including the
enabled compact config; private directory/payload modes were verified.

Scoped review was inline under the approved free-agent quota fallback; no
independent-review pass is claimed. No unresolved important issue was found in
this configuration/test diff. Keep this commit local: no push or PR was
authorized for the dock change.
