# Current desktop recovery — 2026-11-03

This is configuration/source recovery, not an OS image. Keep the existing
CachyOS/ML4W prerequisites. Restore from a logged-out session/TTY where possible;
never run these commands to overwrite a currently edited configuration blindly.

## Order

1. Review `RESTORE.sh --dry-run`. Actual `RESTORE.sh` merges into `$HOME`, builds
   the Rofi plugin/watcher and offers the existing optional Kitty system patch.
   It does not start services, reload Hyprland, download software or send mail.
2. Install the Sherlock runtime/clipboard/icon dependencies below **before the
   next Hyprland login**. Its wrapper is referenced by the shared Hyprland config.
3. For the QS/Pleamar stack coordinator, run the repository-root
   `python3 tools/install_desktop_stack.py --dry-run`, review, then `--apply`.
   Keep the repository at that location. This installs links/guards, not a live switch.
4. Mail additionally needs its private setup below. Do not activate the restored
   mail autostart until it is ready; missing private assets fail closed.
5. Log in/activate the chosen desktop yourself. Reboot, real lock/unlock and
   physical keyboard/mouse behavior were not re-tested during this repository refresh.

`RESTORE.sh` rebases the copied Sherlock TOML/CSS and selected mail/desktop-entry
home paths, and restores owner-private modes required by the mail launcher.
The three-monitor layout and machine-specific app paths still need review.
The Pleamar overlay shares the same Hyprland configuration: restore this ML4W
companion payload first so Sherlock and mail helpers exist. Its old private
snapshot is historical; this PR does not refresh private credential snapshots.

## Sherlock

Saved source/config:

- `~/.config/sherlock/`, `~/.config/hypr/sherlock_session.lua`
- `~/.local/bin/sherlock-launch`
- `~/.local/share/sherlock-integration/` (IPC wrapper, tests, pinned clipboard source)
- `~/.config/systemd/user/sherlock.service`

Install the official Linux x86-64 release **v0.1.14-3** separately from
<https://github.com/Skxxtz/sherlock/releases/tag/v0.1.14-3>.
Verify the archive SHA-256 before extracting:

```text
ea20ce5bdc5805a7e14172576e41ef79c46fbbce1e14db4e9129cfa737f92f9d
```

Install its `sherlock` executable as `~/.local/bin/sherlock`. The expected binary
SHA-256 is `d3f0f11285e2f61af63ef4d3ceac176d8c64c4ad9f149ef9e6c61081e3b21a59`.
The upstream executable reports v0.1.14. Install GTK4/layer-shell and its runtime
dependencies as required by that release, plus Python, cliphist, wl-clipboard and
util-linux/flock. No Sherlock binary or clipboard database is committed.

Build the saved clipboard helper with Rust/Cargo and a C linker:

```sh
cd ~/.local/share/sherlock-integration/upstream-clipboard
cargo build --locked --release
install -Dm755 target/release/sherlock-clp ~/.local/bin/sherlock-clp
```

Source commit: `9c6600d467e1ea81cfd70f8f4fc9b8e135b1363c`; the lockfile's root
package name was corrected in the original session, without changing dependency
versions/checksums. Source license and provenance are included.
If a machine-local Cargo configuration names an unavailable cross-linker, use
`RUSTFLAGS='-C linker=/usr/bin/cc' cargo build --locked --release` for this command
only; do not rewrite global compiler settings.

Install **Tela Circle Dracula** user-locally from the pinned official source:
<https://github.com/vinceliuice/Tela-circle-icon-theme/tree/ee3cf47bcb05c3d99a0860b54254d2ff3d1d2c69>.
Its archive SHA-256 is `2c7e54f707962091a1a762ecc2bd798635a4a83ccacea6db03359f41a7e7ff60`.
Run `./install.sh -d "$HOME/.local/share/icons" dracula` from that verified tree.
Do not change the global GTK/Dolphin theme: only Sherlock's icon path selects it.
Thousands of theme icons are intentionally not vendored.

Hyprland startup owns `sherlock-launch start`; do not also enable a second
autostart mechanism. After installing files, `systemctl --user daemon-reload`
is a manual activation step. Mode changes restart the same service to avoid the
upstream reload loop; ordinary app toggles preserve its PID. Launched apps
survive launcher restarts. Automatic wallpaper-colour refresh remains deferred.
The current CSS is copied as found, including subsequent opacity adjustments.

Offline tests: `python -B -m unittest -v` in the integration directory. GUI burst
and transition scripts are manual probes; this refresh did not run them.

## aerc / Konsole

Only source and explicit preferences are backed up. Do **not** copy the entire
`~/.config/glaze-mail` tree: it contains private browser profiles and mail state.
Excluded: `accounts.conf`, OAuth state/client secrets, drafts/messages, caches,
notification history, private preview output and all virtual environments.

Install aerc, Konsole, Nano, GNOME Text Editor, less, Python/GI and Pillow.
The existing mail helper uses `~/.config/gcal/.venv/bin/python` with
`google-auth`, `google-auth-oauthlib` and their transport dependencies; recreate
that environment without overwriting Calendar credentials. Create the separate
private preview environment using the hash-pinned `requirements-preview.txt`:

```sh
python -m venv --system-site-packages ~/.local/share/glaze-mail/preview-venv
chmod 700 ~/.local/share/glaze-mail/preview-venv
~/.local/share/glaze-mail/preview-venv/bin/python -m pip install --no-deps --only-binary=:all: --require-hashes -r ~/.local/src/glaze-mail/requirements-preview.txt
```

Review the account-specific defaults in `configure.py`/`oauth.py`. For this
original account, supply the Desktop OAuth client privately in the location
required by `oauth.py`; run its `authorize` subcommand yourself. Mail tokens
belong in `~/.local/state/glaze-mail`, never in Calendar state or Git.
Run `configure.py` using the mail environment to generate private account settings;
it refuses to overwrite differing files. No account file or password is restored.
The generator preserves Gmail SMTP over verified TLS and header caching;
Outlook and speculative Go GC changes remain unconfigured.

New previews load permitted HTTPS images by default, as explicitly approved;
this can reveal your IP/open time. Scripts remain blocked, and the compact
bottom footer offers **Block images**. Preview placement is temporary and
mail-specific; it does not change global Brave routing. See the saved mail README.

## External changes recorded, not reproduced automatically

- **Hyprlock 0.9.7:** the session installed a user-local override of the official
  release to avoid lingering lockers. No binary is backed up; install an appropriate
  fixed release separately. `allow_session_lock_restore` stays enabled.
- **Pomo:** external repository `/shared_across_des/repos/pomo`, commit `37c6ca7`,
  bounds hung music-player shutdown to about one second. Rebuild/install there;
  this config repository neither vendors the binary nor alters the timer.
- **Brave Origin:** the user activated the free Linux in-place upgrade. Browser
  Local State/profiles are excluded; re-enable manually if recovering a new profile.
- **CasaOS/Jellyfin trust:** the user opted into Brave's native insecure-origin
  exception for `http://192.168.1.12:8080`, `.12:8096`, `.13:8080`, `.13:8096`.
  This is not TLS/encryption; no wildcard or new exception is applied by restore.
- **Fish/.NET PATH:** the chat diagnosed a resetting `fish_user_paths` assignment,
  but did not apply the proposed fix. It is not silently implemented here.
- Firefox migration and per-tab MPRIS bridges were abandoned/paused; neither is added.
