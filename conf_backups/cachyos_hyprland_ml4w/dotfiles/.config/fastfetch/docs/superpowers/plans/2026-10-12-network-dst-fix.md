# Fastfetch Network DST Fix Implementation Plan

> **For agentic workers:** Use `executing-plans` inline. The user explicitly
> prohibited subagents and approved this bounded timestamp fix with "GO".

**Goal:** Preserve valid billing totals across Cairo DST changes without
pretending an offset-free timestamp identifies which repeated hour was saved.

**Architecture:** Keep the existing single read-only SQLite invocation and
daily aggregation. Convert the saved local timestamp into candidate UTC
instants, validate round trips through Cairo's timezone, and classify freshness
using the current UTC instant. If viable instants disagree about freshness,
keep the total and append `time uncertain` instead of guessing.

**Tech Stack:** Existing SQLite CLI and system timezone database; Python
standard-library tests only. No runtime dependency or background work added.

**Spec:** The user-approved follow-up: small timestamp-check fix with DST
regression tests; preserve the 25th reset, minimal changes, no added resident
resources. Existing accounting requirements remain in
`2026-10-11-network-reset.md`.

## Global Constraints

- Work inline; no subagents.
- Change only `network-usage.sql` and its regression test file.
- Do not change Fastfetch configs, database, daemon, units, retention, or intervals.
- Preserve raw-byte totals, IEC formatting, partial marker, and Cairo's 25th rollover.
- Keep the 200 ms read-only busy timeout and shell error fallback unchanged.
- Preserve normal future tolerance (300 seconds) and stale threshold (600 seconds).
- Cairo DST changes by one hour; test UTC conversion guess and +/-3600 seconds.
- Accept only candidates that round-trip exactly to the saved local timestamp
  and are <= current UTC instant + 300 seconds.
- If all accepted candidates are older than 600 seconds: `stale`.
- If some accepted candidates are older than 600 seconds and some are not:
  `time uncertain`. Missing offset/fold cannot be recovered from vnStat's schema.
- No valid candidate: `network usage unavailable`.
- No Git repository exists; take scoped backups, do not initialize a repository.
- Benchmark actual old and new shell commands, not isolated no-input formatters.

## Review Focus

1. Fresh save before autumn rollback appears later in local wall-clock order.
2. Equal local timestamps from different folds must not prove freshness.
3. Spring clock jump must not add a nonexistent hour to the save's age.
4. Ordinary dates must still enforce exact 5/10-minute thresholds.
5. UTC candidates must neither duplicate byte totals nor remove the daily index seek.

## Task 1: DST Regression Tests and Small Query Fix

**Files:** `/home/narol/.config/fastfetch/network-usage.sql` and
`/home/narol/.config/fastfetch/tests/test_network_usage.py`.

**Interfaces:** `query_at(self, now: str, *, fold: int = 0) -> str` pins both
local and UTC clock expressions in copied query text; no installed test flags.

- [ ] Back up the SQL/tests and hash configs, vnStat configuration, and daemon unit.
- [ ] Add regression tests for autumn fresh, autumn ambiguous, autumn certainly
  stale, first-fold fresh, spring fresh/stale, and unchanged normal thresholds.
  Literal expectations: fresh rows remain `1.00 GiB / 1.00 MiB`; ambiguity
  appends `; time uncertain`, never unavailable or unqualified fresh.
- [ ] Run discovery and observe assertion failures against the current query.
- [ ] Add a UTC epoch to the clock CTE. Remove the naive local future comparison.
  Convert `interface.updated` with `unixepoch(updated, 'utc')`, expand offsets
  `VALUES(-3600),(0),(3600)`, verify
  `datetime(candidate, 'unixepoch', 'localtime') = updated`, filter future
  candidates, then GROUP BY interface id **before** joining daily data.
- [ ] Use min/max UTC age for stale/uncertain markers; leave totals and formatting intact.
- [ ] Run `python -B -m unittest discover -s /home/narol/.config/fastfetch/tests -v`.
  Expect all existing and new tests green; daily aggregation still indexed.

## Task 2: Consistent Test Runner and Final Verification

- [ ] Verify direct execution currently skips nine integration tests.
- [ ] Move `unittest.main()` to the end so direct execution and discovery run
  the identical complete suite; no test logic changes required for this step.
- [ ] Run both test commands and verify equal counts, no skips/failures.
- [ ] Run all three existing Fastfetch configs and check unchanged live layout.
- [ ] Compare actual complete commands with the existing minimal wait4
  supervisor, alternating 200 measurements; label maximum individual-process
  RSS correctly, not aggregate concurrent RAM. Compare against both pre-DST
  query and original vnStat pipeline using backup SQL paths.
- [ ] Inline final review: exact config/system hashes unchanged; no new units
  or resident process; no database edits; only query/tests changed.
- [ ] Record results under `/tmp/opencode` and report the ambiguity limitation.

## Self-Review

- [x] The fix addresses both reproduced autumn cases and the related spring case.
- [x] Byte aggregation is downstream of candidate reduction, preventing double counting.
- [x] Existing normal threshold/cycle/error tests remain binding.
- [x] The user's no-subagent and minimal-resident-resource constraints are preserved.
