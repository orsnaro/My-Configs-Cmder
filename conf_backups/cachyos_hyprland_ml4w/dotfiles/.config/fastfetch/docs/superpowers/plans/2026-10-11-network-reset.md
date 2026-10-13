# Fastfetch Network Billing-Cycle Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Status: awaiting the user's ASTRA review. Do not implement yet.** The user approved the bounded design, then explicitly requested this plan before spawning their reviewer.

**Goal:** Display accurate saved download/upload bytes for eno1's current billing cycle, rolling over at 00:00 on the 25th in Africa/Cairo without additional background CPU/RAM overhead.

**Architecture:** Replace the existing vnStat/awk monthly-summary pipeline with one read-only SQLite query of vnStat's indexed daily records. Calculate the cycle from the current local date, not the latest stored monthly row. All three Fastfetch configurations share one query file; vnstatd continues unchanged.

**Tech Stack:** Existing SQLite CLI 3.53.4, vnStat 2.13 database schema version 1, Fastfetch 2.69.0; Python 3.14 standard-library unittest for tests only.

**Spec:** User-approved bounded design in the conversation: daily byte counts, local midnight on the 25th, shared query across three configs, two-decimal IEC units, partial/stale markers, no new background work. The exact requirements are copied into Global Constraints below. Investigation notes: `/tmp/opencode/fastfetch-network-2026-10-11.md`.

## Global Constraints

- Wait for the user's ASTRA review and approval before modifying production configuration or adding runtime code.
- Reset day is **25**, reset time is **00:00**, timezone is **Africa/Cairo**. The 24th belongs to the old cycle; the 25th belongs to the new one.
- Scope is **this PC's eno1 traffic recorded by vnStat**, not router-wide traffic or an ISP portal quota.
- Read raw integer bytes; sum before formatting. Display `↓ <value> <IEC unit> ↑ <value> <IEC unit> (resets 25th...)` with two decimal places. Zero is `0.00 B`.
- Preserve history. Never reset, rebuild, rewrite, merge, or delete `/var/lib/vnstat/vnstat.db` or any of its records.
- Do not edit `/etc/vnstat.conf`, restart vnstatd, alter its save/poll intervals or data retention, install dependencies, add timers, or add resident processes.
- No additional resident CPU/RAM allocation. Benchmark transient CPU/RAM against the existing pipeline; do not accept a persistent cost or a material per-invocation increase. A transient RAM difference above 2 MiB blocks completion; aim for no increase.
- Database reads stay read-only and have a bounded 200 ms busy timeout. Ignore user SQLite init files; errors produce `network usage unavailable`, never a fabricated zero.
- vnStat currently uses local dates (`UseUTC 0`), `MonthRotate 25`, `DailyDays 62`, `SaveInterval 5`, `UpdateInterval 20`. Leave all unchanged.
- Saved counters normally lag by up to roughly **5 minutes**. This fix does not promise live kernel counters or ISP-equivalent accounting.
- History starts **2026-09-27 19:49:31**, after the current cycle's **2026-09-25 00:00** start. Mark the current cycle `partial`; do not invent September 25–26 usage.
- Append `stale` when `interface.updated` is more than **10 minutes** behind the current local timestamp. Show unavailable for inactive/missing interface, unsupported database schema, or timestamps over **5 minutes in the future**.
- Update only the network command in the three active configs. Preserve every other module, logo, color, and existing backup.
- This configuration directory is **not a Git repository**. Do not create a repository or commit. If this changes before execution, inspect status and create a permitted feature/fix branch before editing code.
- Python test/measurement helpers must have type hints and use only the standard library. They are not invoked by Fastfetch.

## Review Focus

1. **24th/25th with no new database save, or a machine offline over rollover:** select the clock's cycle and return zero/stale, not the newest historical cycle (Task 1).
2. **January rollover, February/leap years, Cairo DST, or a caller's overridden TZ:** calculate calendar dates in Cairo without fixed-second month arithmetic (Tasks 1 and 2).
3. **Mixed old monthly buckets after MonthRotate changed:** daily rows must determine totals and monthly rows must be irrelevant (Task 1).
4. **Missing, locked, corrupt, inactive, or future-dated database state:** return unavailable or visibly stale; never silently assert accurate fresh zero usage (Tasks 1 and 2).
5. **Fresh installation mid-cycle and unit boundaries:** label incomplete history and format summed raw bytes without intermediate rounding (Task 1).

## Evidence and Root Cause

- Active commands are identical at `config.jsonc:111`, `config.ml.jsonc:127`, and `config.gif.jsonc:110`.
- They read fields 9/10 of `vnstat --oneline -i eno1`, then round each to whole units.
- The database was created September 27; `/etc/vnstat.conf` was changed October 1. Setting MonthRotate does not recalculate existing monthly data.
- The database retains an October monthly row while later October traffic is attributed to September under MonthRotate 25. The summary selects October, underreporting the actual recorded cycle.
- Investigation snapshot: displayed bucket RX **7,316,310,251** / TX **1,580,849,115** bytes; daily cycle sum RX **66,668,167,428** / TX **25,745,793,477** bytes. These numbers are observations, not immutable live-test expectations.
- Daily records are ISO local date strings in `day(date, interface, rx, tx)`, indexed uniquely on `(interface, date)`. This cycle requires at most 31 rows; existing retention is sufficient.
- Sources: [vnstat.conf / MonthRotate](https://humdi.net/vnstat/man/vnstat.conf.html), [vnStat v2.13 database implementation](https://github.com/vergoh/vnstat/blob/v2.13/src/dbsql.c).

## Files and Responsibilities

| File | Action | Responsibility |
| --- | --- | --- |
| `/home/narol/.config/fastfetch/network-usage.sql` | Create after approval | Read-only billing-cycle aggregation and display formatting |
| `/home/narol/.config/fastfetch/tests/test_network_usage.py` | Create after approval | Synthetic SQLite fixtures, dates, errors, config integration |
| `/home/narol/.config/fastfetch/config.jsonc` | Network command only | Default/interactive Fastfetch |
| `/home/narol/.config/fastfetch/config.ml.jsonc` | Network command only | Alternative Fastfetch layout |
| `/home/narol/.config/fastfetch/config.gif.jsonc` | Network command only | GIF Fastfetch layout |
| `/tmp/opencode/fastfetch-network-benchmark.py` | Temporary verification helper | Repeatable CPU, latency, and process-memory comparison |
| `/tmp/opencode/fastfetch-network-measure.c` | Temporary verification helper | Minimal-parent wait4 measurements, built with the already-installed cc |
| `/tmp/opencode/fastfetch-network-measure` | Temporary compiled helper | Runs only during benchmarking; never called by Fastfetch |
| `/tmp/opencode/fastfetch-network-verification.md` | Verification report | Tests, measurements, live output, accounting limitations |

## Task 1: Tested Read-Only Billing-Cycle Query

**Files:** Create `network-usage.sql` and `tests/test_network_usage.py` under `/home/narol/.config/fastfetch`.

**Interfaces:**
- Consumes schema version 1: `info(name, value)`, `interface(id, name, active, created, updated)`, `day(interface, date, rx, tx)`.
- Produces exactly one UTF-8 output line on success, formatted as described above; missing/inactive/unsupported/future state produces `network usage unavailable`.
- No runtime parameters or test-mode environment flags. Tests inject deterministic time into a copy of query text, not the installed query or machine clock.
- TestCase helpers: `create_database(self, *, created: str, updated: str, rows: list[tuple[str, int, int]]) -> None` initializes `self.database: Path` inside the test's temporary directory; `query_at(self, now: str) -> str` reads the production SQL and replaces its single `datetime('now', 'localtime')` expression with the fixture timestamp before passing it to the existing CLI against `self.database`.

- [ ] **Step 1: Add failing regression tests.** Use `unittest` and fixture databases under `/tmp/opencode`. Start with the real mixed-bucket regression below; then add the test matrix. Do not alter the live database.

```python
def test_mixed_monthly_buckets_use_daily_bytes(self) -> None:
    self.create_database(
        created="2026-09-27 19:49:31",
        updated="2026-10-11 23:25:00",
        rows=[("2026-09-27", 59351857177, 24164944362),
              ("2026-10-11", 7316310251, 1580849115)],
    )
    self.assertEqual(
        self.query_at("2026-10-11 23:26:00"),
        "↓ 62.09 GiB ↑ 23.98 GiB (resets 25th; partial)",
    )
```

Fixture helpers must initialize schema version 1 and interface eno1 id 1, and support additional interfaces/monthly rows for exclusion tests. A monthly table deliberately containing misleading values must not affect the result. Unless a test explicitly checks partial/stale data, set created before that fixture's cycle start and updated within 10 minutes of its clock.

| Test | Fixture/assertion |
| --- | --- |
| `test_before_reset_includes_previous_25th` | At `2026-10-24 23:59:59`, include Sep 25 through Oct 24; exclude Sep 24 and Oct 25. |
| `test_midnight_starts_new_cycle_without_new_save` | At `2026-10-25 00:00:00`, old rows plus updated Oct 24 23:59 give `↓ 0.00 B ↑ 0.00 B (resets 25th)`; no historical carryover. |
| `test_new_day_accumulates_without_old_history` | Oct 25 row RX 1073741824/TX 524288 yields `↓ 1.00 GiB ↑ 512.00 KiB (resets 25th)`. |
| `test_month_edges` | Subtests Jan 1/24/25, Mar 1/24/25 in 2027 and leap-year 2028; expected cycle start is the most recent calendar 25th. |
| `test_cairo_clock_near_dst` | Local `2026-10-25 00:00:00` and `2026-10-30 00:30:00` both select Oct 25, regardless of UTC offset changes. |
| `test_excludes_other_interface_and_future_daily_rows` | Extra interface id 2 and eno1 rows later than today do not contribute. |
| `test_partial_until_next_cycle` | Created Sep 27: `partial` in September cycle; absent after Oct 25 with a fresh updated timestamp. |
| `test_stale_threshold_and_partial_combination` | Lag exactly 10 minutes: no stale; 10 minutes + 1 second: stale. Partial and stale combine as `; partial; stale`. |
| `test_future_update_threshold` | Updated exactly 5 minutes ahead is accepted; 5 minutes + 1 second ahead yields unavailable. |
| `test_missing_inactive_unsupported_state` | Missing eno1, active=0, or dbversion != `1` each yield unavailable. |
| `test_iec_units_and_sum_before_rounding` | RX/TX cases 0, 1023, 1024, 1048576, 1073741824, 1099511627776; two RX daily rows of 600 bytes yield `1.17 KiB`, not a sum of rounded units. |
| `test_query_never_writes` | Database byte hash and absence of new database/journal files are identical before/after query, including errors and rollover. |

- [ ] **Step 2: Run red.** `python -m unittest discover -s /home/narol/.config/fastfetch/tests -v`. Initially expect failures because the query file does not exist. Separately preserve the already-reproduced original pipeline output versus daily-byte expectation in the regression evidence; a missing file alone is not evidence of the original reset bug. Never count missing dependencies or broken fixtures as reproducing that bug.

- [ ] **Step 3: Implement the query.** Start the file with `.bail on` and `.timeout 200`. Its single clock expression is `datetime('now', 'localtime')`. Use the following exact cycle algorithm:

```sql
WITH clock(local_now) AS (
    SELECT datetime('now', 'localtime')
), bounds AS (
    SELECT local_now,
           date(local_now) AS today,
           strftime('%Y-%m-25', date(local_now, '-24 days')) AS cycle_start
    FROM clock
)
```

Subtracting 24 **calendar days after converting to local time**, then taking that month's 25th, selects the latest billing boundary across all month lengths. Do not subtract `24 * 86400` seconds from a UTC timestamp.

The remainder of the query must:
1. Select eno1 only when active=1, dbversion is `1`, and updated <= `datetime(local_now, '+5 minutes')`.
2. LEFT JOIN `day` on its interface id with date >= cycle_start and date <= today. Use `COALESCE(SUM(rx), 0)`/`COALESCE(SUM(tx), 0)` so a valid new cycle with no saved daily entry yields zero.
3. Keep `created > cycle_start || ' 00:00:00'` and `updated < datetime(local_now, '-10 minutes')` as independent partial/stale flags. Parenthesize concatenation/comparison clearly.
4. Select IEC scale separately for RX and TX using boundaries 1024, 1048576, 1073741824, 1099511627776, 1125899906842624, 1152921504606846976; labels B/KiB/MiB/GiB/TiB/PiB/EiB. Divide using floating point only at formatting time.
5. Use SQL `printf` with `%.2f` and exact output copy; partial/stale suffixes are inside the reset parentheses in that order.
6. Emit `network usage unavailable` if no valid interface/schema state matched. Make aggregation conditional on a valid interface; do not let an empty aggregate manufacture a successful zero row.

- [ ] **Step 4: Run green.** Repeat the full unittest command; all Task 1 cases must pass. Inspect `EXPLAIN QUERY PLAN` and confirm daily aggregation uses the `(interface, date)` index, not a full-database scan.
- [ ] **Step 5: Review checkpoint.** Request spec-compliance and code-quality review of the query/tests. Resolve critical issues before Task 2. No git commit: no repository exists here.

## Task 2: Integrate the Shared Query Without False Zeros

**Files:** Modify only the network `text` value in all three configs; extend `tests/test_network_usage.py`.

**Interfaces:** Consumes Task 1's query file and one-line output. Fastfetch executes this exact shell command, stored with ordinary JSON escaping:

```sh
TZ=Africa/Cairo LC_ALL=C /usr/bin/sqlite3 -readonly -batch -noheader -init /dev/null /var/lib/vnstat/vnstat.db < "$HOME/.config/fastfetch/network-usage.sql" 2>/dev/null || printf '%s\n' 'network usage unavailable'
```

This replaces `vnstat | awk` with one SQLite child. It does not introduce a shell-script wrapper, awk/jq/Python formatter, daemon, or cache. `$HOME` is already supplied to Fastfetch's shell commands.

- [ ] **Step 1: Add failing integration/error tests.** Assert all three modules with key `` and type `command` use exactly the command above. Compare parsed configs with pre-change snapshots after removing only that one `text` value; all other fields must match.
- [ ] **Step 2: Add runtime failure tests.** Against isolated fixture files, test missing/unreadable/corrupt database, missing query file, and an exclusive SQLite writer lock held by another connection. Assert stdout is exactly `network usage unavailable\n`, exit status 0, no added file, and lock handling finishes within 1 second (configured SQLite wait: 200 ms). For unreadable tests, do not run as root.
- [ ] **Step 3: Add environment tests.** Execute the command with inherited `TZ=UTC`, then `TZ=America/New_York`, and a temporary HOME containing a `.sqliterc` that would print extra output. The explicit Cairo TZ must win and the user init file must be ignored. For exact boundary checks, replace only the query's clock expression in the fixture query; never change system time.
- [ ] **Step 4: Run red.** Existing network commands must fail the shared-command assertions before editing configs.
- [ ] **Step 5: Take scoped backups, then edit the three text values.** Save each original under `/tmp/opencode/fastfetch-network-backups/` with its hash. Use targeted patches; do not reformat entire JSON files or overwrite existing `.bak` files.
- [ ] **Step 6: Run green.** Run all unittests. Run Fastfetch with each config in non-graphical `--pipe --logo none` mode and confirm the network line matches standalone query output; no logo/GIF rendering is needed for this verification. Existing disk-module errors from unavailable mounts must be reported separately, not presented as network failures or silently called passing.
- [ ] **Step 7: Review checkpoint.** Review the three scoped diffs, fallback behavior, permissions, and tests. Resolve blockers. No git commit.

## Task 3: Verify Accuracy, Boundaries, and Resource Cost

**Files:** Temporary benchmark helper and verification report under `/tmp/opencode`; no new runtime files.

**Interfaces:** `measure_command(command: str, repetitions: int = 200) -> dict[str, float]` reports median CPU/elapsed milliseconds, CPU distribution, and transient peak memory for the original pipeline and Task 2 command. Benchmark tests/scripts never remain running afterward.

- [ ] **Step 1: Implement the measurement helper.** Build a temporary minimal libc-only C supervisor with the already-installed `cc`: it forks a child that execs `/bin/sh -c <command>`, redirects stdout to `/dev/null`, and calls `wait4` on that shell. Interface: `fastfetch-network-measure <command>` prints elapsed nanoseconds, user/system microseconds, max RSS KiB, and the child's exit status. The typed Python orchestrator warms both commands, alternates old/new order, and gathers at least 200 executions each. CPU includes waited-for pipeline children; keep supervisor costs identical between commands.
- [ ] **Step 2: Measure memory correctly.** Do not use Python's `RUSAGE_CHILDREN` cumulative maximum or a child that inherited the large Python parent's pre-exec high-water mark. The small C supervisor forks only after its own exec, avoiding that artifact for the measured shell. Linux wait4 max RSS is a **maximum individual-process high-water mark**, not the sum of simultaneous pipeline RSS; label it correctly. Also sample `/proc/<pid>/status` for concurrent post-exec shell/vnStat/awk or shell/SQLite memory, and document that millisecond-lived processes may evade peak sampling. Do not claim sampled memory is an exact peak. Use the wait4 comparison as a conservative per-process acceptance check; if it shows an increase, investigate concurrent memory before claiming compliance. No package installation or daemon.
- [ ] **Step 3: Check resident overhead.** Compare vnstatd PID, task count, configured intervals, and service units before/after. The same pre-existing daemon must remain running with no additional persistent process, timer, or altered settings. Record that instantaneous vnstatd RSS may naturally fluctuate; this is not proof of new resident allocation.
- [ ] **Step 4: Verify live byte accuracy from a stable snapshot.** Copy the database through SQLite's read-only backup API to a fixture under `/tmp/opencode`, so vnstatd writes cannot race the comparison. Independently obtain daily raw bytes using `vnstat --db <snapshot> --json d --limit 0 -i eno1` and Python's JSON parser, filter by the expected Cairo cycle, sum, and compare with the new query's formatted output. Never compare snapshot-specific byte totals to an advancing live database.
- [ ] **Step 5: Run the full regression suite and all three live configs again.** Explicitly confirm simulated Oct 24 23:59:59 versus Oct 25 00:00:00 and year/leap boundaries. Simulate via fixtures only; the calendar has not actually reached October 25 yet.
- [ ] **Step 6: Review acceptance results.** Acceptance requires all tests passing, independent daily-byte agreement, confirmed boundary rollover, preserved database/history and config scope, no resident additions, no material median CPU increase, and no transient RAM increase over 2 MiB. If performance fails, pause and refine only this query/command—do not add caching, timers, or a replacement collector without a new approved design.
- [ ] **Step 7: Save the verification report and final-review checkpoint.** Include exact commands, pass counts, measured numbers, limitations, and the fact that September 25–26 was never recorded. Final user summary must distinguish tested midnight rollover from waiting for the real date, and saved PC usage from ISP-wide quota.

## Plan Self-Review / Handoff

- [x] Approved requirements are represented by Tasks 1–3.
- [x] Date, source-data, failure, completeness, precision, and resource risks each have explicit tests/checks.
- [x] No production code or active configuration has been changed while writing this plan.
- [x] Non-Git environment is handled without inappropriate commits or worktree creation.
- [ ] **User's ASTRA agent reviews this plan.**
- [ ] **User approves implementation after review and chooses/preserves an execution approach.**

Recommended execution after ASTRA approval: native implementation with independent checkpoint/final review, because this is one shared query plus three identical one-line integrations. Subagent-driven execution is also supported if the user prefers it. Do not spawn ASTRA on the user's behalf unless requested.
