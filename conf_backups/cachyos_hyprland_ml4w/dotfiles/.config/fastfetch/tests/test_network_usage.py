"""Regression tests for the Fastfetch read-only network billing-cycle query.

Every test names the break it catches and exercises the real sqlite3 CLI
against synthetic databases. Nothing here touches the live vnStat database.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FASTFETCH_DIR = Path("/home/narol/.config/fastfetch")
PRODUCTION_SQL = FASTFETCH_DIR / "network-usage.sql"
SQLITE = "/usr/bin/sqlite3"
CLOCK_EXPRESSION = "datetime('now', 'localtime')"
GIB = 1073741824
MIB = 1048576


def build_fixture_db(
    path: Path,
    *,
    created: str,
    updated: str,
    rows: list[tuple[str, int, int]],
    dbversion: str = "1",
    active: int = 1,
    include_eno1: bool = True,
    other_rows: list[tuple[str, int, int]] | None = None,
    month_rows: list[tuple[str, int, int]] | None = None,
) -> None:
    """Build a schema-version-1 fixture mirroring vnStat's relevant tables."""
    for suffix in ("", "-journal", "-wal", "-shm"):
        stale = Path(str(path) + suffix) if suffix else path
        if stale.exists():
            stale.unlink()
    con = sqlite3.connect(path)
    try:
        con.execute(
            "CREATE TABLE info(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, value TEXT NOT NULL)"
        )
        con.execute(
            "CREATE TABLE interface(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, alias TEXT,"
            " active INTEGER NOT NULL, created DATE NOT NULL, updated DATE NOT NULL,"
            " rxcounter INTEGER NOT NULL, txcounter INTEGER NOT NULL,"
            " rxtotal INTEGER NOT NULL, txtotal INTEGER NOT NULL)"
        )
        con.execute(
            "CREATE TABLE day(id INTEGER PRIMARY KEY, interface INTEGER REFERENCES interface(id) ON DELETE CASCADE,"
            " date DATE NOT NULL, rx INTEGER NOT NULL, tx INTEGER NOT NULL,"
            " CONSTRAINT u UNIQUE (interface, date))"
        )
        con.execute(
            "CREATE TABLE month(id INTEGER PRIMARY KEY, interface INTEGER REFERENCES interface(id) ON DELETE CASCADE,"
            " date DATE NOT NULL, rx INTEGER NOT NULL, tx INTEGER NOT NULL,"
            " CONSTRAINT u UNIQUE (interface, date))"
        )
        con.execute("INSERT INTO info(name, value) VALUES('dbversion', ?)", (dbversion,))
        con.execute("INSERT INTO info(name, value) VALUES('vnstatversion', '2.13')")
        if include_eno1:
            con.execute(
                "INSERT INTO interface(name, alias, active, created, updated, rxcounter, txcounter, rxtotal, txtotal)"
                " VALUES('eno1', '', ?, ?, ?, 0, 0, 0, 0)",
                (active, created, updated),
            )
            eno1_id = 1
            for day, rx, tx in rows:
                con.execute(
                    "INSERT INTO day(interface, date, rx, tx) VALUES(?, ?, ?, ?)",
                    (eno1_id, day, rx, tx),
                )
            for day, rx, tx in month_rows or []:
                con.execute(
                    "INSERT INTO month(interface, date, rx, tx) VALUES(?, ?, ?, ?)",
                    (eno1_id, day, rx, tx),
                )
        if other_rows:
            con.execute(
                "INSERT INTO interface(name, alias, active, created, updated, rxcounter, txcounter, rxtotal, txtotal)"
                " VALUES('eth0', '', 1, '2026-08-01 00:00:00', '2026-10-11 12:00:00', 0, 0, 0, 0)"
            )
            other_id = con.execute(
                "SELECT id FROM interface WHERE name='eth0'"
            ).fetchone()[0]
            for day, rx, tx in other_rows:
                con.execute(
                    "INSERT INTO day(interface, date, rx, tx) VALUES(?, ?, ?, ?)",
                    (other_id, day, rx, tx),
                )
        con.commit()
    finally:
        con.close()


class NetworkUsageQueryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ff-net-")
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / "vnstat.db"

    def create_database(
        self,
        *,
        created: str,
        updated: str,
        rows: list[tuple[str, int, int]],
        dbversion: str = "1",
        active: int = 1,
        include_eno1: bool = True,
        other_rows: list[tuple[str, int, int]] | None = None,
        month_rows: list[tuple[str, int, int]] | None = None,
    ) -> None:
        build_fixture_db(
            self.database,
            created=created,
            updated=updated,
            rows=rows,
            dbversion=dbversion,
            active=active,
            include_eno1=include_eno1,
            other_rows=other_rows,
            month_rows=month_rows,
        )

    def query_at(self, now: str, *, fold: int = 0) -> str:
        """Pin copied query clocks to a Cairo instant, including its DST fold."""
        sql = PRODUCTION_SQL.read_text(encoding="utf-8")
        self.assertEqual(
            sql.count(CLOCK_EXPRESSION),
            1,
            "production query must contain exactly one clock expression",
        )
        pinned = sql.replace(CLOCK_EXPRESSION, f"'{now}'", 1)
        instant = datetime.fromisoformat(now).replace(
            tzinfo=ZoneInfo("Africa/Cairo"), fold=fold
        )
        pinned = pinned.replace("unixepoch('now')", str(int(instant.timestamp())), 1)
        script = Path(self.tmp.name) / "pinned.sql"
        script.write_text(pinned, encoding="utf-8")
        env = dict(os.environ, TZ="Africa/Cairo", LC_ALL="C")
        proc = subprocess.run(
            [SQLITE, "-readonly", "-batch", "-noheader", "-init", "/dev/null", str(self.database)],
            input=script.read_bytes(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=10,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"sqlite3 failed: {proc.stderr.decode()!r}")
        return proc.stdout.decode("utf-8").rstrip("\n")

    def test_mixed_monthly_buckets_use_daily_bytes(self) -> None:
        """Old monthly rows keep stale buckets after MonthRotate changes; daily rows decide."""
        self.create_database(
            created="2026-09-27 19:49:31",
            updated="2026-10-11 23:25:00",
            rows=[("2026-09-27", 59351857177, 24164944362), ("2026-10-11", 7316310251, 1580849115)],
        )
        self.assertEqual(
            self.query_at("2026-10-11 23:26:00"),
            "↓ 62.09 GiB ↑ 23.98 GiB (resets 25th; partial)",
        )

    def test_monthly_rows_are_ignored(self) -> None:
        """A misleading monthly table must not move the daily-byte total."""
        month_rows = [("2026-09-01", 1, 2), ("2026-10-01", 7316310251, 1580849115)]
        self.create_database(
            created="2026-09-27 19:49:31",
            updated="2026-10-11 23:25:00",
            rows=[("2026-09-27", 59351857177, 24164944362), ("2026-10-11", 7316310251, 1580849115)],
            month_rows=month_rows,
        )
        self.assertEqual(
            self.query_at("2026-10-11 23:26:00"),
            "↓ 62.09 GiB ↑ 23.98 GiB (resets 25th; partial)",
        )

    def test_before_reset_includes_previous_25th(self) -> None:
        """Oct 24 still belongs to the cycle that started Sep 25."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-24 23:59:59",
            rows=[
                ("2026-09-24", 10 * GIB, 10 * MIB),
                ("2026-09-25", 1 * GIB, 1 * MIB),
                ("2026-10-24", 2 * GIB, 2 * MIB),
                ("2026-10-25", 9 * GIB, 9 * MIB),
            ],
        )
        self.assertEqual(
            self.query_at("2026-10-24 23:59:59"),
            "↓ 3.00 GiB ↑ 3.00 MiB (resets 25th)",
        )

    def test_midnight_starts_new_cycle_without_new_save(self) -> None:
        """The clock alone starts the new cycle even before vnstatd saves Oct 25."""
        self.create_database(
            created="2026-09-27 19:49:31",
            updated="2026-10-24 23:59:00",
            rows=[("2026-09-27", 59351857177, 24164944362), ("2026-10-24", 2147483648, 2097152)],
        )
        self.assertEqual(
            self.query_at("2026-10-25 00:00:00"),
            "↓ 0.00 B ↑ 0.00 B (resets 25th)",
        )

    def test_new_day_accumulates_without_old_history(self) -> None:
        """Oct 25 traffic counts immediately and old history does not carry over."""
        self.create_database(
            created="2026-09-27 19:49:31",
            updated="2026-10-25 12:00:00",
            rows=[
                ("2026-09-27", 59351857177, 24164944362),
                ("2026-10-25", 1073741824, 524288),
            ],
        )
        self.assertEqual(
            self.query_at("2026-10-25 12:00:00"),
            "↓ 1.00 GiB ↑ 512.00 KiB (resets 25th)",
        )

    def test_month_edges(self) -> None:
        """January, short February, leap days, and 31-day months all use the calendar 25th."""
        cases = [
            ("2027-01-01 12:00:00", "2026-12-25", "2026-12-24", [("2026-12-25", 1 * GIB, MIB), ("2027-01-01", 2 * GIB, 2 * MIB)]),
            ("2027-01-24 12:00:00", "2026-12-25", "2026-12-24", [("2026-12-25", 1 * GIB, MIB), ("2027-01-24", 2 * GIB, 2 * MIB)]),
            ("2027-01-25 00:00:01", "2027-01-25", "2027-01-24", [("2027-01-25", 3 * GIB, 3 * MIB)]),
            ("2027-03-01 12:00:00", "2027-02-25", "2027-02-24", [("2027-02-25", 1 * GIB, MIB), ("2027-03-01", 2 * GIB, 2 * MIB)]),
            ("2027-03-24 12:00:00", "2027-02-25", "2027-02-24", [("2027-02-25", 1 * GIB, MIB), ("2027-03-24", 2 * GIB, 2 * MIB)]),
            ("2027-03-25 00:00:01", "2027-03-25", "2027-03-24", [("2027-03-25", 3 * GIB, 3 * MIB)]),
            ("2028-02-25 00:00:01", "2028-02-25", "2028-02-24", [("2028-02-25", 3 * GIB, 3 * MIB)]),
            ("2028-02-29 12:00:00", "2028-02-25", "2028-02-24", [("2028-02-25", 1 * GIB, MIB), ("2028-02-29", 2 * GIB, 2 * MIB)]),
            ("2028-03-01 12:00:00", "2028-02-25", "2028-02-24", [("2028-02-25", 1 * GIB, MIB), ("2028-03-01", 2 * GIB, 2 * MIB)]),
        ]
        for now, start, before, included in cases:
            with self.subTest(now=now, start=start):
                self.create_database(
                    created="2026-01-01 00:00:00",
                    updated=now,
                    rows=[(before, 10 * GIB, 100 * MIB)] + included,
                )
                _ = start
                self.assertEqual(
                    self.query_at(now),
                    "↓ 3.00 GiB ↑ 3.00 MiB (resets 25th)",
                )

    def test_cairo_clock_near_dst(self) -> None:
        """Both sides of the late-October DST change still select the Oct 25 cycle."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-25 00:00:00",
            rows=[("2026-10-24", 5 * GIB, 5 * MIB), ("2026-10-25", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-25 00:00:00"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)",
        )
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-30 00:30:00",
            rows=[
                ("2026-10-24", 5 * GIB, 5 * MIB),
                ("2026-10-25", 1 * GIB, 1 * MIB),
                ("2026-10-30", 2 * GIB, 2 * MIB),
            ],
        )
        self.assertEqual(
            self.query_at("2026-10-30 00:30:00"),
            "↓ 3.00 GiB ↑ 3.00 MiB (resets 25th)",
        )

    def test_excludes_other_interface_and_future_daily_rows(self) -> None:
        """Another interface and days after today must not leak into eno1's cycle."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-11 12:00:00",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB), ("2026-10-12", 9 * GIB, 9 * MIB)],
            other_rows=[("2026-10-11", 8 * GIB, 80 * MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-11 12:00:00"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)",
        )

    def test_autumn_rollback_preserves_recent_save(self) -> None:
        """23:55 +03 to 23:02 +02 is seven minutes, not a future save."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-29 23:55:00",
            rows=[("2026-10-29", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-29 23:02:00", fold=1),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)",
        )

    def test_autumn_equal_wall_times_do_not_prove_freshness(self) -> None:
        """Equal 23:57 timestamps could mean zero or sixty minutes elapsed."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-29 23:57:00",
            rows=[("2026-10-29", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-29 23:57:00", fold=1),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; time uncertain)",
        )

    def test_autumn_first_fold_save_is_unambiguously_fresh(self) -> None:
        """The second occurrence is still in the future during the first fold."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-29 23:55:00",
            rows=[("2026-10-29", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-29 23:57:00", fold=0),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)",
        )

    def test_autumn_stale_when_every_candidate_is_old(self) -> None:
        """Both possible 23:30 occurrences are old at 23:50 in the second fold."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-29 23:30:00",
            rows=[("2026-10-29", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-29 23:50:00", fold=1),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; stale)",
        )

    def test_autumn_uncertainty_clears_after_stale_threshold(self) -> None:
        """The ambiguous save becomes certainly stale once its latest age is >10min."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-29 23:57:00",
            rows=[("2026-10-29", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-30 00:07:00"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; time uncertain)",
        )
        self.assertEqual(
            self.query_at("2026-10-30 00:07:01"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; stale)",
        )

    def test_spring_jump_uses_elapsed_seconds(self) -> None:
        """23:55 +02 to 01:02 +03 crosses a missing hour but is only seven minutes."""
        self.create_database(
            created="2026-01-01 00:00:00",
            updated="2026-04-23 23:55:00",
            rows=[("2026-04-23", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-04-24 01:02:00"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)",
        )
        self.assertEqual(
            self.query_at("2026-04-24 01:06:00"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; stale)",
        )

    def test_nonexistent_spring_save_is_unavailable(self) -> None:
        """The skipped 00:30 local time cannot represent a real daemon save."""
        self.create_database(
            created="2026-01-01 00:00:00",
            updated="2026-04-24 00:30:00",
            rows=[("2026-04-24", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-04-24 01:32:00"), "network usage unavailable"
        )

    def test_partial_and_ambiguous_freshness_keep_both_markers(self) -> None:
        self.create_database(
            created="2026-10-26 12:00:00",
            updated="2026-10-29 23:57:00",
            rows=[("2026-10-29", GIB, MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-29 23:57:00", fold=1),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; partial; time uncertain)",
        )

    def test_partial_until_next_cycle(self) -> None:
        """History starting Sep 27 marks the Sep 25 cycle partial, then clears on Oct 25."""
        self.create_database(
            created="2026-09-27 19:49:31",
            updated="2026-10-11 12:00:00",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-11 12:00:00"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; partial)",
        )
        self.create_database(
            created="2026-09-27 19:49:31",
            updated="2026-10-26 12:00:00",
            rows=[("2026-10-26", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(
            self.query_at("2026-10-26 12:00:00"),
            "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)",
        )

    def test_stale_threshold_and_partial_combination(self) -> None:
        """Exactly 10 minutes lag is fresh; one second more is stale."""
        now = "2026-10-11 12:00:00"
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-11 11:50:00",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(self.query_at(now), "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)")
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-11 11:49:59",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(self.query_at(now), "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; stale)")
        self.create_database(
            created="2026-10-01 00:00:01",
            updated="2026-10-11 11:49:59",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(
            self.query_at(now), "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th; partial; stale)"
        )

    def test_future_update_threshold(self) -> None:
        """A 5-minute clock skew is tolerated; anything beyond is unavailable, not zero."""
        now = "2026-10-11 12:00:00"
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-11 12:05:00",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(self.query_at(now), "↓ 1.00 GiB ↑ 1.00 MiB (resets 25th)")
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-11 12:05:01",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
        )
        self.assertEqual(self.query_at(now), "network usage unavailable")

    def test_missing_inactive_unsupported_state(self) -> None:
        """Missing, disabled, or wrong-schema state must never print a false zero."""
        with self.subTest(state="missing interface"):
            self.create_database(
                created="2026-08-01 00:00:00",
                updated="2026-10-11 12:00:00",
                rows=[],
                include_eno1=False,
            )
            self.assertEqual(self.query_at("2026-10-11 12:00:00"), "network usage unavailable")
        with self.subTest(state="inactive interface"):
            self.create_database(
                created="2026-08-01 00:00:00",
                updated="2026-10-11 12:00:00",
                rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
                active=0,
            )
            self.assertEqual(self.query_at("2026-10-11 12:00:00"), "network usage unavailable")
        for bad_version in ("0", "2"):
            with self.subTest(state=f"dbversion {bad_version}"):
                self.create_database(
                    created="2026-08-01 00:00:00",
                    updated="2026-10-11 12:00:00",
                    rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
                    dbversion=bad_version,
                )
                self.assertEqual(
                    self.query_at("2026-10-11 12:00:00"), "network usage unavailable"
                )

    def test_iec_units_and_sum_before_rounding(self) -> None:
        """Units use binary boundaries and raw bytes are summed before formatting."""
        cases = [
            (0, "↓ 0.00 B ↑ 0.00 B (resets 25th)"),
            (1023, "↓ 1023.00 B ↑ 0.00 B (resets 25th)"),
            (1024, "↓ 1.00 KiB ↑ 0.00 B (resets 25th)"),
            (1048576, "↓ 1.00 MiB ↑ 0.00 B (resets 25th)"),
            (1073741824, "↓ 1.00 GiB ↑ 0.00 B (resets 25th)"),
            (1099511627776, "↓ 1.00 TiB ↑ 0.00 B (resets 25th)"),
        ]
        for value, expected in cases:
            with self.subTest(bytes=value):
                self.create_database(
                    created="2026-08-01 00:00:00",
                    updated="2026-10-11 12:00:00",
                    rows=[("2026-10-11", value, 0)],
                )
                self.assertEqual(self.query_at("2026-10-11 12:00:00"), expected)
        with self.subTest(bytes="600+600 RX"):
            self.create_database(
                created="2026-08-01 00:00:00",
                updated="2026-10-11 12:00:00",
                rows=[("2026-10-10", 600, 0), ("2026-10-11", 600, 0)],
            )
            self.assertEqual(
                self.query_at("2026-10-11 12:00:00"), "↓ 1.17 KiB ↑ 0.00 B (resets 25th)"
            )
        with self.subTest(bytes="600+600 TX"):
            self.create_database(
                created="2026-08-01 00:00:00",
                updated="2026-10-11 12:00:00",
                rows=[("2026-10-10", 0, 600), ("2026-10-11", 0, 600)],
            )
            self.assertEqual(
                self.query_at("2026-10-11 12:00:00"), "↓ 0.00 B ↑ 1.17 KiB (resets 25th)"
            )

    def test_query_never_writes(self) -> None:
        """Valid, rollover, and unavailable queries leave bytes and journals untouched."""
        self.create_database(
            created="2026-09-27 19:49:31",
            updated="2026-10-24 23:59:00",
            rows=[("2026-10-24", 2 * GIB, 2 * MIB)],
        )
        before = hashlib.sha256(self.database.read_bytes()).hexdigest()
        self.assertEqual(
            self.query_at("2026-10-25 00:00:00"), "↓ 0.00 B ↑ 0.00 B (resets 25th)"
        )
        self.assertEqual(self.query_at("2026-10-24 23:59:00"), "↓ 2.00 GiB ↑ 2.00 MiB (resets 25th; partial)")
        missing = Path(self.tmp.name) / "missing.db"
        saved, self.database = self.database, missing
        try:
            self.create_database(
                created="2026-08-01 00:00:00",
                updated="2026-10-11 12:00:00",
                rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
                active=0,
            )
            missing_before = hashlib.sha256(missing.read_bytes()).hexdigest()
            self.assertEqual(
                self.query_at("2026-10-11 12:00:00"), "network usage unavailable"
            )
            self.assertEqual(hashlib.sha256(missing.read_bytes()).hexdigest(), missing_before)
        finally:
            self.database = saved
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(), before)
        leftovers = sorted(
            p.name
            for p in Path(self.tmp.name).glob("*.db-*")
            if p.suffix in (".journal", ".wal", ".shm") or "-journal" in p.name or "-wal" in p.name
        )
        self.assertEqual(leftovers, [])

    def test_daily_aggregation_uses_index(self) -> None:
        """The cycle sum must seek the (interface, date) index, not scan history."""
        self.create_database(
            created="2026-08-01 00:00:00",
            updated="2026-10-11 12:00:00",
            rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
        )
        sql = PRODUCTION_SQL.read_text(encoding="utf-8")
        body = sql[sql.index("WITH") :].replace(CLOCK_EXPRESSION, "'2026-10-11 12:00:00'", 1)
        proc = subprocess.run(
            [SQLITE, "-readonly", "-batch", "-noheader", "-init", "/dev/null", str(self.database)],
            input=f"EXPLAIN QUERY PLAN {body}".encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        plan = proc.stdout.decode("utf-8")
        self.assertIn("day", plan)
        self.assertIn("INDEX", plan)


EXPECTED_COMMAND = (
    "TZ=Africa/Cairo LC_ALL=C /usr/bin/sqlite3 -readonly -batch -noheader"
    " -init /dev/null /var/lib/vnstat/vnstat.db"
    ' < "$HOME/.config/fastfetch/network-usage.sql" 2>/dev/null'
    " || printf '%s\\n' 'network usage unavailable'"
)
CONFIG_NAMES = ("config.jsonc", "config.ml.jsonc", "config.gif.jsonc")
BACKUP_DIR = Path("/tmp/opencode/fastfetch-network-backups")
NETWORK_KEY = "\uf6ff"


def network_module(config: dict) -> dict:
    found = [
        m
        for m in config["modules"]
        if m.get("key") == NETWORK_KEY and m.get("type") == "command"
    ]
    assert len(found) == 1, f"expected exactly one network command module, got {len(found)}"
    return found[0]


class NetworkCommandIntegrationTest(unittest.TestCase):
    """The three Fastfetch configs must share one read-only command with a safe fallback."""

    def run_shell_command(
        self, db: Path, sql: Path, extra_env: dict[str, str] | None = None
    ) -> tuple[int, str, float]:
        import shlex
        import time

        command = (
            "TZ=Africa/Cairo LC_ALL=C /usr/bin/sqlite3 -readonly -batch -noheader"
            f" -init /dev/null {shlex.quote(str(db))}"
            f" < {shlex.quote(str(sql))} 2>/dev/null"
            " || printf '%s\\n' 'network usage unavailable'"
        )
        env = dict(os.environ, **(extra_env or {}))
        start = time.perf_counter()
        proc = subprocess.run(
            ["/bin/sh", "-c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=10,
            check=False,
        )
        return proc.returncode, proc.stdout.decode("utf-8"), time.perf_counter() - start

    def test_all_configs_use_shared_command(self) -> None:
        for name in CONFIG_NAMES:
            with self.subTest(config=name):
                config = __import__("json").loads((FASTFETCH_DIR / name).read_text())
                self.assertEqual(network_module(config)["text"], EXPECTED_COMMAND)

    def test_script_mode_can_run_integration_test(self) -> None:
        """Direct execution must define integration tests before unittest starts."""
        result = subprocess.run(
            [sys.executable, "-B", __file__,
             "NetworkCommandIntegrationTest.test_corrupt_database_falls_back"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 1 test", result.stderr)
        self.assertIn("OK", result.stderr)

    def test_only_network_command_changed(self) -> None:
        import json

        for name in CONFIG_NAMES:
            with self.subTest(config=name):
                before = json.loads((BACKUP_DIR / name).read_text())
                after = json.loads((FASTFETCH_DIR / name).read_text())
                network_module(before)["text"] = ""
                network_module(after)["text"] = ""
                self.assertEqual(after, before)

    def test_missing_database_falls_back(self) -> None:
        missing = Path(tempfile.gettempdir()) / "ff-net-definitely-missing.db"
        if missing.exists():
            missing.unlink()
        rc, out, _ = self.run_shell_command(missing, PRODUCTION_SQL)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "network usage unavailable\n")
        self.assertFalse(missing.exists(), "fallback must not create a database file")

    def test_corrupt_database_falls_back(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ff-net-corrupt-") as tmp:
            corrupt = Path(tmp) / "corrupt.db"
            corrupt.write_bytes(b"this is not a sqlite database at all" * 10)
            before = corrupt.read_bytes()
            rc, out, _ = self.run_shell_command(corrupt, PRODUCTION_SQL)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "network usage unavailable\n")
            self.assertEqual(corrupt.read_bytes(), before)

    @unittest.skipIf(os.geteuid() == 0, "unreadable-file test is meaningless as root")
    def test_unreadable_database_falls_back(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ff-net-unread-") as tmp:
            locked = Path(tmp) / "locked.db"
            con = sqlite3.connect(locked)
            try:
                con.execute("CREATE TABLE t(x)")
                con.commit()
            finally:
                con.close()
            locked.chmod(0o000)
            try:
                rc, out, _ = self.run_shell_command(locked, PRODUCTION_SQL)
            finally:
                locked.chmod(0o600)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "network usage unavailable\n")

    def test_missing_query_file_falls_back(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ff-net-nosql-") as tmp:
            db = Path(tmp) / "v.db"
            con = sqlite3.connect(db)
            try:
                con.execute("CREATE TABLE t(x)")
                con.commit()
            finally:
                con.close()
            rc, out, _ = self.run_shell_command(db, Path(tmp) / "no-such.sql")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "network usage unavailable\n")

    def test_locked_database_falls_back_within_one_second(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ff-net-locked-") as tmp:
            db = Path(tmp) / "v.db"
            build_fixture_db(
                db,
                created="2026-08-01 00:00:00",
                updated="2026-10-11 12:00:00",
                rows=[("2026-10-11", 1 * GIB, 1 * MIB)],
            )
            con = sqlite3.connect(db, timeout=5.0, isolation_level=None)
            try:
                con.execute("BEGIN EXCLUSIVE")
                rc, out, elapsed = self.run_shell_command(db, PRODUCTION_SQL)
            finally:
                try:
                    con.rollback()
                finally:
                    con.close()
            self.assertEqual(rc, 0)
            self.assertEqual(out, "network usage unavailable\n")
            self.assertGreaterEqual(
                elapsed, 0.15, f"returned in {elapsed:.3f}s without waiting on the lock"
            )
            self.assertLess(elapsed, 1.0, f"lock wait took {elapsed:.3f}s, timeout is 200ms")

    def test_user_sqliterc_is_ignored(self) -> None:
        import json

        with tempfile.TemporaryDirectory(prefix="ff-net-home-") as home:
            poisoned = Path(home, ".sqliterc")
            poisoned.write_text(".print POISONED-BY-INIT\n", encoding="utf-8")
            env = dict(os.environ, HOME=home)
            with_flag_file = subprocess.run(
                [SQLITE, "-batch", "-noheader", "-init", str(poisoned), ":memory:"],
                input=b"SELECT 1;",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                timeout=10,
                check=False,
            )
            self.assertIn(
                b"POISONED-BY-INIT",
                with_flag_file.stdout,
                "control: an init file selected by -init must affect output",
            )
            with_devnull = subprocess.run(
                [SQLITE, "-batch", "-noheader", "-init", "/dev/null", ":memory:"],
                input=b"SELECT 1;",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                timeout=10,
                check=False,
            )
            self.assertEqual(
                with_devnull.stdout, b"1\n", "-init /dev/null must ignore the rc file"
            )
            config = json.loads((FASTFETCH_DIR / "config.jsonc").read_text())
            self.assertIn("-init /dev/null", network_module(config)["text"])

    def test_explicit_cairo_tz_wins_over_inherited_tz(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        expected = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d")
        for hostile in ("UTC", "America/New_York", "Pacific/Kiritimati"):
            with self.subTest(inherited_tz=hostile):
                env = dict(os.environ, TZ=hostile)
                proc = subprocess.run(
                    ["/bin/sh", "-c", "TZ=Africa/Cairo /usr/bin/sqlite3 -batch -noheader -init /dev/null ':memory:' \"SELECT date('now','localtime');\""],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout.decode().strip(), expected)


if __name__ == "__main__":
    unittest.main()
