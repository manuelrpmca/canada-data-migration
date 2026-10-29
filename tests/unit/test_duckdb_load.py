from datetime import date, datetime

import pytest

from cdm.load import duckdb as warehouse
from cdm.sources import Observation

NOW = datetime(2026, 1, 10, 15, 0)


@pytest.fixture
def con(tmp_path):
    con = warehouse.connect(tmp_path / "test.duckdb")
    yield con
    con.close()


def upsert(con, observations, run_id="run-1"):
    return warehouse.upsert_observations(
        con, source="valet", series_key="usd_cad", series_id="FXUSDCAD",
        observations=observations, run_id=run_id, payload_hash="h", now=NOW,
    )  # fmt: skip


def test_first_load_inserts_everything(con):
    counts = upsert(con, [Observation(date(2026, 1, 2), 1.1), Observation(date(2026, 1, 5), 1.2)])
    assert (counts.received, counts.inserted, counts.updated, counts.unchanged) == (2, 2, 0, 0)


def test_second_identical_load_changes_nothing(con):
    rows = [Observation(date(2026, 1, 2), 1.1), Observation(date(2026, 1, 5), 1.2)]
    upsert(con, rows)
    counts = upsert(con, rows, run_id="run-2")
    assert (counts.inserted, counts.updated, counts.unchanged) == (0, 0, 2)
    # The rows still point at the run that wrote them.
    assert con.execute("SELECT DISTINCT run_id FROM raw.observations").fetchall() == [("run-1",)]


def test_revision_updates_only_the_changed_row(con):
    upsert(con, [Observation(date(2026, 1, 2), 1.1), Observation(date(2026, 1, 5), 1.2)])
    counts = upsert(
        con, [Observation(date(2026, 1, 2), 1.1), Observation(date(2026, 1, 5), 1.25)], "run-2"
    )
    assert (counts.inserted, counts.updated, counts.unchanged) == (0, 1, 1)
    value, run_id = con.execute(
        "SELECT value, run_id FROM raw.observations WHERE ref_date = DATE '2026-01-05'"
    ).fetchone()
    assert (value, run_id) == (1.25, "run-2")


def test_duplicate_dates_in_one_payload_keep_the_last_value(con):
    counts = upsert(con, [Observation(date(2026, 1, 2), 1.0), Observation(date(2026, 1, 2), 2.0)])
    assert counts.received == 1
    assert con.execute("SELECT value FROM raw.observations").fetchone() == (2.0,)


def test_latest_ref_date(con):
    assert warehouse.latest_ref_date(con, "valet", "usd_cad") is None
    upsert(con, [Observation(date(2026, 1, 2), 1.1), Observation(date(2026, 1, 5), 1.2)])
    assert warehouse.latest_ref_date(con, "valet", "usd_cad") == date(2026, 1, 5)


def test_empty_payload_is_a_no_op(con):
    counts = upsert(con, [])
    assert (counts.received, counts.inserted, counts.updated, counts.unchanged) == (0, 0, 0, 0)
