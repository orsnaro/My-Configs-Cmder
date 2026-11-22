.bail on
.timeout 200
WITH clock(local_now, now_epoch) AS (
    SELECT datetime('now', 'localtime'), unixepoch('now')
), bounds AS (
    SELECT local_now,
           date(local_now) AS today,
           strftime('%Y-%m-25', date(local_now, '-24 days')) AS cycle_start
    FROM clock
), ver AS (
    SELECT value AS dbversion FROM info WHERE name = 'dbversion'
), raw_iface AS (
    SELECT interface.id AS id,
           interface.created AS created,
           interface.updated AS updated,
           unixepoch(interface.updated, 'utc') AS utc_guess
    FROM interface, ver
    WHERE interface.name = 'eno1'
      AND interface.active = 1
      AND ver.dbversion = '1'
), offsets(seconds) AS (
    VALUES (-3600), (0), (3600)
), iface AS (
    -- Cairo repeats one hour; retain only UTC instants mapping to the saved time.
    SELECT raw_iface.id, raw_iface.created,
           MIN(clock.now_epoch - (raw_iface.utc_guess + offsets.seconds)) AS min_age,
           MAX(clock.now_epoch - (raw_iface.utc_guess + offsets.seconds)) AS max_age
    FROM raw_iface, clock, offsets
    WHERE datetime(raw_iface.utc_guess + offsets.seconds, 'unixepoch', 'localtime') = raw_iface.updated
      AND raw_iface.utc_guess + offsets.seconds <= clock.now_epoch + 300
    GROUP BY raw_iface.id
), totals AS (
    SELECT
        COALESCE(SUM(day.rx), 0) AS rx,
        COALESCE(SUM(day.tx), 0) AS tx
    FROM day
    WHERE day.interface = (SELECT id FROM iface)
       AND day.date >= (SELECT cycle_start FROM bounds)
       AND day.date <= (SELECT today FROM bounds)
), units(scale, label) AS (
    VALUES (1152921504606846976.0, 'EiB'),
           (1125899906842624.0, 'PiB'),
           (1099511627776.0, 'TiB'),
           (1073741824.0, 'GiB'),
           (1048576.0, 'MiB'),
           (1024.0, 'KiB'),
           (1.0, 'B')
), display_unit AS (
    -- Both directions share the unit selected by the larger byte total.
    SELECT scale, label
    FROM units, totals
    WHERE scale <= MAX(totals.rx, totals.tx) OR scale = 1.0
    ORDER BY scale DESC
    LIMIT 1
)
SELECT CASE
    WHEN iface.id IS NULL THEN 'network usage unavailable'
    ELSE printf(
        '↓ %.1f ↑ %.1f %s%s',
        totals.rx / display_unit.scale,
        totals.tx / display_unit.scale,
        display_unit.label,
        ' ( 25th'
            || CASE WHEN (iface.created > ((SELECT cycle_start FROM bounds) || ' 00:00:00')) THEN '; partial' ELSE '' END
            -- A lost DST fold cannot prove freshness; keep totals and report doubt.
            || CASE WHEN iface.min_age > 600 THEN '; stale'
                    WHEN iface.max_age > 600 THEN '; time uncertain' ELSE '' END
            || ')'
    )
END
FROM bounds LEFT JOIN iface ON 1 = 1, totals, display_unit;
