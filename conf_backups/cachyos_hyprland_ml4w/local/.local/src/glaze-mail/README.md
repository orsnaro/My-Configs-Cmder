# Glaze Mail local helpers

The managed mail launcher is `~/.local/bin/glaze-mail`. Konsole/aerc and dedicated
children belong to `glaze-mail-eval.service`; closing mail does not auto-restart it.
Gmail sending is configured for `omar.rashad.dev@gmail.com`; activate account
changes with the user-controlled restart described below. Delete/archive
shortcuts can still change server mail. No Outlook account is configured.

## Navigation and mail font

**j** selects the previous tab; **l** selects the next tab from the message list,
opened-message viewer, and compose review. They remain ordinary letters in Nano,
address/subject fields, and pager passthrough. **i/k**, capitals, and arrow keys
are unchanged; these shortcuts do not switch focus between panes.
Run `:reload -B` in aerc to activate binding changes.

New mail windows use a mail-only 10pt Konsole font (previously 11pt); other
Konsole profiles are unchanged. This takes effect on the next user-controlled
mail launch. To shrink the existing window without closing a draft, press
**Ctrl+-** once; no automatic mail restart is needed or performed.

## Mail-only history and header cache

New managed mail windows disable Konsole terminal scrollback with the launch-only
`HistoryMode=0` override. Aerc/less navigation is unchanged; other Konsole profiles,
Kitty and Alacritty settings are untouched.

Gmail header caching is enabled. Previously fetched headers/metadata can be reused
across launches from `~/.config/glaze-mail/terminal/cache/aerc`; this is not a
full-message/attachment cache or a RAM-saving setting. Metadata remains on disk,
and Gmail synchronization is still required. The first uncached visit still fetches
the required headers.

Both settings take effect after saving drafts and closing/reopening mail yourself.
No automatic restart is performed; `:reload -C`/`:reload -B` cannot activate these
launcher/account changes.

## Compose and reply

Composing/replying uses Nano inside aerc; opening plain-text messages still uses
standalone GNOME Text Editor. In Nano, **Ctrl+O**, then **Enter** saves; **F2**
exits to aerc's review screen. **Ctrl+X** remains aerc's command prompt shortcut.
After changing the editor, run `:reload -C` in aerc before starting a new compose.

From a draft in the message list or ordinary viewer, `:recall -s` opens compose
review without entering Nano. **y** invokes send only from that review screen.

## Gmail sending

Outgoing mail uses Gmail SMTP with certificate-verified TLS and XOAUTH2, reusing
the existing separately authorized mail token helper. No password/token is stored
in accounts.conf, and no Calendar credentials are changed. The SMTP login was
verified without submitting a message; actual delivery has not been tested.

Aerc cannot reload accounts.conf. If a compose/draft is open, save it first:
from compose review press **p** to postpone it (in Nano, save with **Ctrl+O**, then
**Enter**, and exit with **F2** first). Confirm it is saved, then close and reopen
mail normally. `:reload -C` and `:reload -B` do not activate account changes.
Reopen the saved draft, finish editing and exit Nano with **F2**, or use
`:recall -s` to go straight to review. Press **y** only when ready to send.
No automatic restart or test email is performed by the setup.

## HTML preview

Once activated, HTML is selected before plaintext. `o`/`O` open the selected HTML
part as a sanitized local page in the normal HTTPS-default browser/profile.
With Brave on Hyprland, each preview opens in standard app mode, without the
normal browser toolbar or tab bar, tiled directly to the right of aerc at startup,
without moving/swapping it after opening. It keeps the
normal browser profile; multiple previews use separate windows, not tabs.
Placement targets the preview/aerc pair, without changing browser defaults or
global compositor rules for other browser/webapp windows.
The preview-only startup hook is temporary; it does not edit saved Hyprland
settings. If preparation fails, the helper refuses to open a misplaced preview.
Plain-text-only parts still open in standalone GNOME Text Editor; attachments
retain their normal handlers. Existing scrolling/navigation/search keys remain.

Scripts are always blocked. New previews load permitted HTTPS images by default,
directly contacting image hosts and potentially revealing your IP and message open.
The compact image notice stays at the bottom of the window. Use **Block images**
there to switch this preview to the remote-images-blocked page;
it cannot undo requests already sent.
Embedded safe raster images remain visible. Formatting can be simpler than Gmail.
Local preview files are removed when mail closes; rendered windows/tabs/history are not
erased, and their local Load/Block links stop working after that cleanup.

The first activation needs a user-controlled mail close/reopen so the service can
own cleanup. Do not reload only aerc's config into an old service invocation.

## Tests

Run `make test` here. It runs both suites, without skips:

- `tests/`: existing OAuth/mail/launcher/config tests using the existing mail venv.
- `tests_preview/`: preview safety/file/desktop tests using the isolated preview venv.

The preview venv is private and reuses installed GI/Pillow read-only. Its only added
dependency is hash-pinned in `requirements-preview.txt`; do not install it in the
Calendar/OAuth venv or global Python environment. Installation:

```sh
python -m venv --system-site-packages ~/.local/share/glaze-mail/preview-venv
~/.local/share/glaze-mail/preview-venv/bin/python -m pip install --no-deps --only-binary=:all: --require-hashes -r requirements-preview.txt
```

Native aerc/browser/network/lifecycle checks are recorded separately under
`~/.opencode/plan/.execution/2026-11-01-html-preview/`; unit tests alone do not prove
browser privacy or live Gmail delivery. Initial preview activation completed with
the user's controlled mail close/reopen. Workspace-placement checks are recorded
under `~/.opencode/plan/.execution/2026-11-01-html-workspace/`; this helper-only
follow-up needs no mail restart. App-mode/right-side placement checks are under
`~/.opencode/plan/.execution/2026-11-02-html-app-right/`.
Direct first-layout placement and bottom-notice browser checks are under
`~/.opencode/plan/.execution/2026-11-02-preview-first-layout/`; reopen a preview
to get the updated notice. No mail restart or saved compositor reload is needed.
