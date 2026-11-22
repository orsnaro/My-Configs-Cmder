# PR #10 security review — 2026-10-28

Reviewed the actual `github-advanced-security` comments on head `9c3e77a`.
CodeQL analysis completed, but its alert check failed on the two findings below.
GitGuardian reported success. No alerts were dismissed, no GitHub replies were
posted, and no security-sensitive runtime/source changes were authorized here.

Both findings concern the upstream TV-remote helper copied into the backup:
`conf_backups/cachyos_hyprland_pleamar/source/vitreus/bin/vitreus-tvremote`.
They are not findings against the desktop stack switcher.

## 1. TLS version policy — CodeQL High

Comment: https://github.com/orsnaro/My-Configs-Cmder/pull/10#discussion_r4403041210

`connect_tls()` (lines 197–203) uses `SSLContext(PROTOCOL_TLS_CLIENT)` without an
explicit `minimum_version`. On this installed Python, a direct local check
returns `TLSv1_2`; the bot's assertion that TLS 1.0/1.1 are currently enabled
does not match this runtime. Nevertheless, explicitly raising
`ctx.minimum_version` to at least `ssl.TLSVersion.TLSv1_2`, while keeping
any stricter runtime minimum, would make the policy independent of older
defaults and is a reasonable narrow hardening change. A minimum does not cap
newer TLS versions; certificate/public-key pinning is a separate identity policy.

Do not replace the paired TV protocol with ordinary public-CA verification
blindly: the TV uses its own certificate. Separately, the current code sets
`check_hostname=False` and `CERT_NONE`; initial pairing hashes the peer's key,
but subsequent reconnects only check an empty `paired-<host>` marker and do not
pin the server certificate. Server identity on reconnect therefore deserves a
separate security fix/design; adding a TLS floor alone does not solve it.

## 2. All-interface binding — CodeQL Medium

Comment: https://github.com/orsnaro/My-Configs-Cmder/pull/10#discussion_r4403041240

`scan()` (lines 354–396) binds `('', 0)` on a UDP socket, sends an mDNS request
to `224.0.0.251:5353`, receives discovery replies for roughly three seconds, then
closes in `finally`. This is not a persistent TCP control server, but the
wildcard bind does expose the transient receive socket on every interface.

Replacing it with `127.0.0.1` would prevent LAN TV discovery. Appropriate
hardening is to scope discovery to an explicitly chosen LAN interface/address
and validate discovery responses; alternatively, document the intentionally
required network scope for review. Do not suppress the finding or claim the
scanner is safe solely because it is short-lived. No TV/network scan was run
for this review.

## Backup integrity and recommendation

The helper was captured byte-for-byte, not authored as part of the switcher.
Any approved patch must be kept distinct from the original snapshot or applied
to the installed source and then re-exported with updated hashes/tests. Editing
only the public payload would invalidate its source-parity claims.

Recommended order: explicit TLS floor with regression coverage; deliberate
server-certificate pinning on reconnect; interface-scoped discovery after
confirming the desired LAN/multi-interface behavior. These need their own
approval and must not be mixed silently into the clipboard correction.

References:
- https://codeql.github.com/codeql-query-help/python/py-insecure-protocol/
- https://codeql.github.com/codeql-query-help/python/py-bind-socket-all-network-interfaces/
