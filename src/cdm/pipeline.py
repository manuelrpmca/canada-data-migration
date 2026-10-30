"""Ingestion run: for each series, compute the request window, fetch, land, upsert, log."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import httpx

from cdm.landing import land
from cdm.load import duckdb as warehouse
from cdm.settings import Series
from cdm.sources import FetchResult, statcan, valet


@dataclass(frozen=True)
class SeriesResult:
    series_key: str
    status: str  # success | failed | skipped
    request_start: date | None = None
    received: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    message: str = ""


def new_run_id(now: datetime) -> str:
    return f"{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"


def request_start(series: Series, latest: date | None) -> date:
    """First date to request: full backfill when empty, else latest loaded minus the lookback."""
    if latest is None:
        return series.start_date
    if series.frequency == "daily":
        start = latest - timedelta(days=series.lookback)
    else:
        month_index = latest.year * 12 + (latest.month - 1) - series.lookback
        start = date(month_index // 12, month_index % 12 + 1, 1)
    return max(start, series.start_date)


def fetch(client: httpx.Client, series: Series, start: date) -> FetchResult:
    if series.source == "valet":
        return valet.fetch_observations(client, series.series_id, start)
    return statcan.fetch_observations(client, series.series_id, start)


def ingest(
    series_list: list[Series],
    con: duckdb.DuckDBPyConnection,
    client: httpx.Client,
    data_root: Path,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[SeriesResult]:
    run_id = new_run_id(clock())
    results = []
    for series in series_list:
        started_at = clock()
        if not series.ready:
            result = SeriesResult(series.key, "skipped", message="no series_id yet; run cdm verify")
            _log(con, run_id, series, started_at, clock(), result)
            results.append(result)
            continue
        start = request_start(series, warehouse.latest_ref_date(con, series.source, series.key))
        landed = None
        try:
            fetched = fetch(client, series, start)
            landed = land(fetched.raw, data_root, series.source, series.key, run_id)
            counts = warehouse.upsert_observations(
                con,
                source=series.source,
                series_key=series.key,
                series_id=series.series_id,
                observations=fetched.observations,
                run_id=run_id,
                payload_hash=landed.sha256,
                now=_naive_utc(clock()),
            )
            result = SeriesResult(
                series.key, "success", start,
                counts.received, counts.inserted, counts.updated, counts.unchanged,
            )  # fmt: skip
        except Exception as exc:  # one failing series must not stop the others
            message = f"{type(exc).__name__}: {exc}"
            result = SeriesResult(series.key, "failed", start, message=message)
        _log(con, run_id, series, started_at, clock(), result, landed)
        results.append(result)
    return results


def _naive_utc(moment: datetime) -> datetime:
    """DuckDB TIMESTAMP columns hold naive UTC."""
    return moment.astimezone(UTC).replace(tzinfo=None)


def _log(con, run_id, series, started_at, finished_at, result, landed=None) -> None:
    warehouse.log_run(
        con,
        run_id=run_id,
        source=series.source,
        series_key=series.key,
        started_at=_naive_utc(started_at),
        finished_at=_naive_utc(finished_at),
        status=result.status,
        request_start=result.request_start,
        rows_received=result.received,
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
        landing_file=str(landed.path) if landed else None,
        payload_hash=landed.sha256 if landed else None,
        message=result.message or None,
    )
