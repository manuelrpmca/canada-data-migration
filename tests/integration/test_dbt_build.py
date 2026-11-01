"""End-to-end check of the dbt project on a small synthetic warehouse. No network.

The data is generated, not recorded: two years of weekday rates and monthly values, loaded
through the same loader functions the pipeline uses, so `dbt build` sees real raw tables.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from cdm import transform
from cdm.load import duckdb as warehouse
from cdm.settings import Series
from cdm.sources import Observation

NOW = datetime(2026, 1, 10, 15, 0)
START = date(2024, 1, 1)
END = date(2025, 12, 31)

SERIES = [
    Series("usd_cad", "valet", "FXUSDCAD", "USD/CAD", "CAD per USD", "daily", START, 14, True),
    Series("policy_rate", "valet", "V39079", "Policy rate", "percent", "daily", START, 14, True),
    Series("cpi_ontario", "statcan", "1", "CPI", "index", "monthly", START, 3, True, 1),
    Series("unemployment_ontario", "statcan", "2", "Unemp", "pct", "monthly", START, 3, True, 2),
]  # fmt: skip


def _weekdays():
    day = START
    while day <= END:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def _month_starts():
    return [date(y, m, 1) for y in (2024, 2025) for m in range(1, 13)]


def _load(con, key, source, observations):
    warehouse.upsert_observations(
        con, source=source, series_key=key, series_id=key, observations=observations,
        run_id="synthetic", payload_hash="synthetic", now=NOW,
    )  # fmt: skip


@pytest.fixture
def synthetic_warehouse(tmp_path):
    db_path = tmp_path / "warehouse.duckdb"
    con = warehouse.connect(db_path)
    warehouse.sync_series(con, SERIES, NOW)
    weekdays = list(_weekdays())
    months = _month_starts()
    _load(con, "usd_cad", "valet", [Observation(d, 1.35) for d in weekdays])
    _load(con, "policy_rate", "valet", [Observation(d, 3.0) for d in weekdays])
    _load(con, "cpi_ontario", "statcan", [Observation(m, 160.0 + i) for i, m in enumerate(months)])
    _load(con, "unemployment_ontario", "statcan", [Observation(m, 7.0) for m in months])
    con.close()
    return db_path


def test_dbt_build_passes(synthetic_warehouse):
    assert transform.build(synthetic_warehouse)


def test_dbt_build_fails_on_an_implausible_value(synthetic_warehouse):
    con = warehouse.connect(synthetic_warehouse)
    con.execute("UPDATE raw.observations SET value = 99 WHERE series_key = 'policy_rate'")
    con.close()
    assert not transform.build(synthetic_warehouse)
