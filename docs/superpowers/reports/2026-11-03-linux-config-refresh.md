# Linux configuration refresh — 2026-11-03

## Scope and outcome

Refreshed the public desktop backups using the final decisions in the relevant
November 1–3 OpenCode sessions. No chat transcripts, credentials or private
recovery snapshots were published. Work is isolated from the original dirty
checkout on `chore/refresh-linux-configs-20261103`, based on `origin/main` at
`6e128ea`.

- Carried forward the previously unpublished native Rofi reliability work.
- Sherlock is the primary Hyprland launcher; current wrapper/service, source,
  configuration, tests and dependency provenance are saved. Rofi stays fallback.
- Both Hyprland exports agree on current workspace/app routing, Sherlock
  toggle/outside dismissal, and CasaOS/Jellyfin-only tiled title-bar suppression.
- Matching QS workspace labels and persistent Kitty ANSI-green override included.
- Saved explicit aerc/Konsole preferences and reviewed mail/preview source, not
  mutable mail directories or account/auth files. SMTP/header-cache defaults
  remain in the generator; actual mail credentials must be authorized separately.
- Backup/restore now includes these dependencies; restoration rebases copied
  home paths and restores the mail launcher's required private file modes.
- Server-app desktop entries and their two icons are included, using Ethernet.
- External Hyprlock/Pomo changes and manual Brave settings are documented rather
  than vendored as binaries or browser profiles. No Firefox migration or media
  bridge is introduced.

Recovery instructions: `conf_backups/cachyos_hyprland_ml4w/CURRENT-RESTORE.md`.

## Verification performed

All 12 existing/discovered offline Python unittest groups ran in separate
processes: **622 discovered, 620 passed, 2 explicitly skipped, 0 failures**.
The skips are the same focused-GUI Kitty resize test in the two exports; no
new skip, xfail or blanket exception was added. `pytest` is not installed, so
the repository's unittest discovery commands were used directly.

| Group | Discovered | Result |
| --- | ---: | --- |
| Fastfetch | 33 | passed |
| ML4W Kitty | 52 | 51 passed, 1 existing GUI skip |
| Sherlock integration | 36 | passed |
| Mail helpers | 63 | passed |
| Safe HTML preview | 44 | passed |
| ML4W backup/restore | 10 | passed |
| Pleamar Kitty | 52 | 51 passed, 1 existing GUI skip |
| Vitreus scene/helper regressions | 205 | passed |
| Pleamar restore | 13 | passed |
| Desktop stack and refresh | 92 | passed |
| Migration | 17 | passed |
| QS launcher routing | 5 | passed |

The new isolated Hyprland snapshot test executes all **19 Lua/shell harnesses
plus Sherlock's session harness for each export**. It uses a disposable home,
the actual saved helpers and their existing command fixtures, not live apps.

Both real restore scripts passed preview **and actual apply** in a fresh
temporary home containing spaces. Rofi's plugin/native watcher rebuilt there;
Sherlock paths, mail permissions and absent account files were checked. No
service activation, compositor reload, browser launch, mail send or live-config
write was performed. Public manifests contain **706 ML4W files** and
**498 Pleamar entries**.

Changed/new Bash, Lua, TOML and Python sources passed syntax validation.
`git diff --check` passed. Changed/new files were screened for private-state
paths, known token/key formats, compiled ELF files and build/cache artifacts.
The clipboard helper builds with its locked dependencies using a command-local
`/usr/bin/cc` linker override; upstream defines **zero unit tests**, so that is
build evidence, not additional test coverage.

## Failures found and resolved honestly

- Main's TLS change lowered an existing TLS 1.3 platform minimum to 1.2. The
  original failing regression remains intact; the helper now raises only old
  minima and never lowers stricter policy. TLS 1.2 remains the floor.
- Six older Hyprland harnesses did not model binding handles, layers or animation
  APIs used by the actual launcher modules. Their mocks were completed without
  disabling launcher code; standalone session tests exercise real callbacks.
- The old Gmail launcher assertion expected the obsolete URL, not the approved
  account-specific URL. The executable command is still tested with fake Brave.
- Mail's test hardcoded its original installation directory. It now locates the
  checked-out preview source; production mail behavior is unchanged.
- ML4W Kitty's stale Alt-arrow expectation contradicted the saved letters-only
  mapping. The already-correct Pleamar regression was carried over.
- Fastfetch tests read the live home and missing `/tmp` migration fixtures.
  They now exercise the committed SQL with genuine `26ace17` baseline configs;
  previously accepted ASCII-logo/CPU/volume-query customizations are explicitly
  checked, not overwritten. Production Fastfetch configuration is unchanged.
- New restore tests caught absent-payload mutation and unquoted desktop-entry
  paths with spaces. Both failed first, then passed after scoped fixes.

## Review and rulings

Independent exploration/review agents were attempted on the configured free
model, but all were provider-quota blocked. No model escalation occurred.
Specification and code-quality review continued as separate inline passes.

Rulings:

1. Continue inline after quota failure; cost: no independent second reviewer.
2. Publish from current main, not the old dirty branch; cost: unpublished work
   must be explicitly carried over. The relevant seven Rofi commits were retained.
3. Preserve Sherlock's existing shared Hyprland-start lifecycle rather than add
   new stack ownership; cost: it remains resident across shell switches as in the
   captured setup. No new watchdog/backend/theme watcher was added.
4. Repair stale test fixtures/contracts rather than change accepted desktop
   settings to satisfy them; cost: historical baselines need explicit provenance,
   which is included alongside the fixtures.

No critical/important review issue remains identified in the scoped refresh.
The worktree is retained for PR feedback; nothing is merged automatically.

## Explicit limits

No new live GUI/physical-input, reboot/login, lock/unlock, remote-server, browser
security, end-to-end Gmail delivery or performance benchmark is claimed. Manual
GUI probes and the existing Kitty GUI skip remain visible. Earlier live reports
are historical evidence, not rerun by this refresh. The October private recovery
snapshot is unchanged and intentionally not committed.
