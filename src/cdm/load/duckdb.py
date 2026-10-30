"""DuckDB loader: idempotent upsert on (source, series_key, ref_date) plus a run log (ADR 0005).

The upsert is written as explicit UPDATE + INSERT inside one transaction, so the counts of
inserted / updated / unchanged rows come from the same comparison that changes the data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

from cdm.sources import Observation

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.observations (
    source        VARCHAR   NOT NULL,
    series_key    VARCHAR   NOT NULL,
    series_id     VARCHAR   NOT NULL,
    ref_date      DATE      NOT NULL,
    value         DOUBLE    NOT NULL,
    ingested_at   TIMESTAMP NOT NULL,  -- first time this key was loaded
    updated_at    TIMESTAMP NOT NULL,  -- last time its value changed
    run_id        VARCHAR   NOT NULL,  -- run that last wrote the row
    payload_hash  VARCHAR   NOT NULL,  -- sha256 of the landed file that last wrote the row
    PRIMARY KEY (source, series_key, ref_date)
);

CREATE TABLE IF NOT EXISTS raw.run_log (
    run_id         VARCHAR   NOT NULL,
    source         VARCHAR   NOT NULL,
    series_key     VARCHAR   NOT NULL,
    started_at     TIMESTAMP NOT NULL,
    finished_at    TIMESTAMP NOT NULL,
    status         VARCHAR   NOT NULL,  -- success | failed | skipped
    request_start  DATE,
    rows_received  INTEGER,
    inserted       INTEGER,
    updated        INTEGER,
    unchanged      INTEGER,
    landing_file   VARCHAR,
    payload_hash   VARCHAR,
    message        VARCHAR
);
"""


@dataclass(frozen=True)
class LoadCounts:
    received: int
    inserted: int
    updated: int
    unchanged: int


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA_SQL)
    return con


def latest_ref_date(con: duckdb.DuckDBPyConnection, source: str, series_key: str) -> date | None:
    row = con.execute(
        "SELECT max(ref_date) FROM raw.observations WHERE source = ? AND series_key = ?",
        [source, series_key],
    ).fetchone()
    return row[0] if row else None


def upsert_observations(
    con: duckdb.DuckDBPyConnection,
    *,
    source: str,
    series_key: str,
    series_id: str,
    observations: list[Observation],
    run_id: str,
    payload_hash: str,
    now: datetime,
) -> LoadCounts:
    # Last value wins if the payload repeats a date.
    by_date = {o.ref_date: o.value for o in observations}
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("CREATE OR REPLACE TEMP TABLE incoming (ref_date DATE, value DOUBLE)")
        if by_date:
            con.executemany("INSERT INTO incoming VALUES (?, ?)", list(by_date.items()))
        inserted, updated = con.execute(
            """
            SELECT
                count(*) FILTER (WHERE t.ref_date IS NULL),
                count(*) FILTER (WHERE t.ref_date IS NOT NULL AND t.value IS DISTINCT FROM i.value)
            FROM incoming i
            LEFT JOIN raw.observations t
              ON t.source = ? AND t.series_key = ? AND t.ref_date = i.ref_date
            """,
            [source, series_key],
        ).fetchone()
        con.execute(
            """
            UPDATE raw.observations AS t
            SET value = i.value, updated_at = ?, run_id = ?, payload_hash = ?
            FROM incoming i
            WHERE t.source = ? AND t.series_key = ? AND t.ref_date = i.ref_date
              AND t.value IS DISTINCT FROM i.value
            """,
            [now, run_id, payload_hash, source, series_key],
        )
        con.execute(
            """
            INSERT INTO raw.observations
            SELECT ?, ?, ?, i.ref_date, i.value, ?, ?, ?, ?
            FROM incoming i
            WHERE NOT EXISTS (
                SELECT 1 FROM raw.observations t
                WHERE t.source = ? AND t.series_key = ? AND t.ref_date = i.ref_date
            )
            """,
            [source, series_key, series_id, now, now, run_id, payload_hash, source, series_key],
        )
        con.execute("DROP TABLE incoming")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    received = len(by_date)
    return LoadCounts(received, inserted, updated, received - inserted - updated)


def log_run(con: duckdb.DuckDBPyConnection, **fields) -> None:
    columns = [
        "run_id", "source", "series_key", "started_at", "finished_at", "status",
        "request_start", "rows_received", "inserted", "updated", "unchanged",
        "landing_file", "payload_hash", "message",
    ]  # fmt: skip
    values = [fields.get(c) for c in columns]
    placeholders = ", ".join("?" for _ in columns)
    con.execute(f"INSERT INTO raw.run_log ({', '.join(columns)}) VALUES ({placeholders})", values)


def status(con: duckdb.DuckDBPyConnection) -> list[tuple]:
    """Per series: rows, first and last reference date, and the latest run's outcome."""
    return con.execute(
        """
        WITH last_run AS (
            SELECT series_key, status, inserted, updated, unchanged, finished_at,
                   row_number() OVER (PARTITION BY series_key ORDER BY finished_at DESC) AS rn
            FROM raw.run_log
        )
        SELECT o.series_key, count(*), min(o.ref_date), max(o.ref_date),
               r.status, r.inserted, r.updated, r.unchanged, r.finished_at
        FROM raw.observations o
        LEFT JOIN last_run r ON r.series_key = o.series_key AND r.rn = 1
        GROUP BY ALL
        ORDER BY o.series_key
        """
    ).fetchall()
