# VS Code OSS configuration backup

Privacy-filtered snapshot of **Default** and **C# .NET** on Linux, taken on
2026-10-28 from Code - OSS 1.138.0. This is a manual backup, not automatic sync.

## Contents

| Path | Contents |
| --- | --- |
| `user/settings.json` | Default settings; saved SSH host mappings removed |
| `user/keybindings.json` | Default keyboard shortcuts |
| `user/profiles/42e8a6f6/settings.json` | C# .NET settings |
| `profiles/*.code-profile` | Portable profile-import files |
| `profiles.json` | Profile names and snapshot file locations |
| `extensions/*.json` | Installed versions, release/pin/scope flags, and disabled states |
| `extensions/*.txt` | Installed extension IDs with exact recorded versions |
| `runtime/argv.json` | Allowlisted runtime option: crash reporting disabled |
| `manifest.json` | Snapshot metadata, counts, and exclusions |
| `SHA256SUMS` | Checksums for every other file in this directory |

Default has **75 installed extensions**, of which **32 are disabled**. C# .NET
has **13 installed extensions**, of which **1 is disabled**. Disabled built-in
extension states are also preserved for both profiles. Five disabled-but-uninstalled
IDs in Default are recorded separately; importing must not install them merely
because a stale disabled-state record exists.

C# .NET had no separate shortcuts file. Neither profile had user tasks or custom
snippets at snapshot time; the empty chat-model configuration is not included.

## Privacy and intentional exclusions

Only the configuration files listed above were selected. No whole user-data
directory or credential database was copied.

- `remote.SSH.remotePlatform` is emptied in both the copied Default settings
  and its portable export. Saved hostnames/IP addresses are not published.
- The runtime crash-reporter identifier and `password-store` override are
  omitted. Configure your operating system credential store locally; do not
  copy another machine's keyring setup or use basic storage as a backup method.
- Account tokens, API keys, passwords, extension login/connection storage,
  database connections, global/workspace storage, local history, chat history,
  logs, workspace-to-profile associations, old backups, and extension binaries
  are excluded. Secrets and remote connections must be configured locally.
- Settings and shortcuts otherwise preserve the source configuration. Machine
  dependencies such as fonts, the .NET SDK, and Konsole are not bundled.

The plain files and decoded export resources were checked for credential-like
assignments, token/private-key patterns, saved hosts, and machine identifiers.
Review future changes before publishing: settings can contain secrets even
though credential storage itself is excluded.

## Verify the download

From this directory:

```sh
sha256sum -c SHA256SUMS
```

## Restore portable profiles

Back up your current editor configuration before replacing settings or applying
extensions. Start with new profiles to avoid changing a working setup.

1. Open the editor's **Profiles** editor, then the **New Profile** dropdown.
2. Select **Import Profile...** and choose `profiles/csharp-dotnet.code-profile`.
3. Review its settings/extensions and select **Create** with the name **C# .NET**.
4. Repeat with `profiles/default.code-profile`, naming the new profile
   **Default Backup** to avoid colliding with the built-in **Default** profile.
5. Switch to each profile and review the Extensions view, including disabled
   extensions. Reassociate project folders with the desired profile manually.

If your editor version offers **Apply Profile**, use it only when deliberately
replacing the active profile's configuration. It may replace its extension set.

To restore the actual built-in **Default** profile rather than keep a separate
Default Backup profile, switch to Default and use **Preferences: Open User
Settings (JSON)** and **Preferences: Open Keyboard Shortcuts (JSON)** to restore
the corresponding `user/` files. Restore its extensions using the inventory
below, and disable the IDs recorded in `extensions/default.json` through the
Extensions view. Do not copy the source profile ID into the editor's storage:
the importer generates its own profile locations.

### Extension versions and disabled state

The JSON inventories record exact installed versions and disabled IDs per
profile. Portable imports follow the native export convention: pinned
extensions request their recorded version; other extensions request the current
compatible release, preserving pre-release preference where relevant.

For an exact-version restore, use entries from the matching `.txt` inventory:

```sh
code-oss --profile "C# .NET" --install-extension jakubkozera.csharp-dev-tools@1.15.5
code-oss --profile "C# .NET" --install-extension jomblebee.jomblebee-csharp-solution-explorer@0.16.0
```

Repeat for the required entries and select the correct profile name. CLI
installation alone does **not** restore disabled state; review the matching
JSON inventory in the Extensions view. An exact version may no longer be
available for your editor/platform. Review failures instead of silently
substituting another version. Imported/CLI-pinned versions can affect later
automatic updates; review update/pin behavior in the Extensions view.

Open VSX and Microsoft Marketplace availability/licenses differ. Some
extensions may need a publisher-provided VSIX or may not support your editor.
No extension packages are redistributed in this backup.

### Runtime options and machine-specific settings

**Preferences: Configure Runtime Arguments** opens your local `argv.json`.
Merge the single option from `runtime/argv.json` if wanted; do not overwrite
your existing file or its machine-generated identifiers. Restart the editor
after changing runtime arguments. Reconfigure SSH hosts and any ignored
machine-specific settings locally. Profile import can intentionally ignore
machine-scoped settings; the readable settings files preserve the safe values
for manual review if needed.

## Sync, Code - OSS, and VSCodium

This installation has no Microsoft Settings Sync service configured, and no
third-party sync extension was installed at snapshot time. Signing into an
account for an extension does not itself enable settings/profile sync.

Code - OSS and VSCodium use the same open-source editor core; VSCodium is a
separate community distribution with privacy-focused build patches. This
Code - OSS installation already uses Open VSX. Neither switching distributions
nor importing these files enables account sync automatically. Open VSX is an
extension registry; a `.vsix` file is an installable extension package.

## Verification and references

Verified: source fidelity except documented redactions; nested profile resource
schema; extension versions/enablement; file allowlist; privacy-pattern checks;
checksums; and the original checkout's unchanged files. Profile imports are
**not GUI-tested**; extension downloads/availability were not exercised.
The refreshed keyboard resources use the native numeric `Platform.Linux` value
(`2`), correcting the previous string metadata without changing shortcuts.

- [Profiles and import workflow](https://code.visualstudio.com/docs/configure/profiles)
- [Microsoft Settings Sync](https://code.visualstudio.com/docs/configure/settings-sync)
- [Profile resource interfaces](https://github.com/microsoft/vscode/blob/main/src/vs/workbench/services/userDataProfile/common/userDataProfile.ts)
- [Keyboard resource schema](https://github.com/microsoft/vscode/blob/main/src/vs/workbench/services/userDataProfile/browser/keybindingsResource.ts)
- [Extension export/import behavior](https://github.com/microsoft/vscode/blob/main/src/vs/workbench/services/userDataProfile/browser/extensionsResource.ts)
- [VSCodium](https://vscodium.com/)
- [VSCodium extension registry and compatibility](https://github.com/VSCodium/vscodium/blob/master/docs/extensions.md)
- [VSCodium migration and backup options](https://github.com/VSCodium/vscodium/blob/master/docs/migration.md)
