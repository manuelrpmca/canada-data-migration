import json
from dataclasses import replace
from datetime import UTC, date, datetime

import httpx
import pytest

from cdm import pipeline
from cdm.http import make_client
from cdm.load import duckdb as warehouse


def test_request_start_backfills_when_empty(daily_series):
    assert pipeline.request_start(daily_series, None) == daily_series.start_date


def test_request_start_daily_lookback(daily_series):
    assert pipeline.request_start(daily_series, date(2026, 3, 20)) == date(2026, 3, 6)


@pytest.mark.parametrize(
    ("latest", "expected"),
    [(date(2026, 3, 1), date(2025, 12, 1)), (date(2026, 1, 1), date(2025, 10, 1))],
)
def test_request_start_monthly_lookback_crosses_years(monthly_series, latest, expected):
    assert pipeline.request_start(monthly_series, latest) == expected


def test_request_start_never_before_start_date(daily_series):
    assert pipeline.request_start(daily_series, date(2026, 1, 3)) == daily_series.start_date


@pytest.fixture
def valet_client(fixture_bytes):
    return make_client(
        httpx.MockTransport(
            lambda request: httpx.Response(200, content=fixture_bytes("valet_observations.json"))
        )
    )


def clock():
    return datetime(2026, 1, 10, 15, 0, tzinfo=UTC)


def test_ingest_twice_is_idempotent(tmp_path, daily_series, valet_client):
    con = warehouse.connect(tmp_path / "w.duckdb")
    first = pipeline.ingest([daily_series], con, valet_client, tmp_path, clock=clock)
    second = pipeline.ingest([daily_series], con, valet_client, tmp_path, clock=clock)

    assert (first[0].status, first[0].inserted) == ("success", 4)
    assert (second[0].inserted, second[0].updated, second[0].unchanged) == (0, 0, 4)
    assert con.execute("SELECT count(*) FROM raw.observations").fetchone() == (4,)
    assert con.execute("SELECT count(*) FROM raw.run_log").fetchone() == (2,)
    landed = sorted((tmp_path / "raw" / "valet" / "usd_cad").glob("*.json"))
    assert len(landed) == 2


def test_series_without_identifier_is_skipped(tmp_path, daily_series, valet_client):
    con = warehouse.connect(tmp_path / "w.duckdb")
    pending = replace(daily_series, key="cpi_ontario", source="statcan", series_id=None)
    results = pipeline.ingest([pending], con, valet_client, tmp_path, clock=clock)
    assert results[0].status == "skipped"
    assert con.execute("SELECT status FROM raw.run_log").fetchone() == ("skipped",)


def test_one_failing_series_does_not_stop_the_others(tmp_path, daily_series, fixture_bytes):
    def handler(request):
        if "V39079" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, content=fixture_bytes("valet_observations.json"))

    broken = replace(daily_series, key="policy_rate", series_id="V39079")
    con = warehouse.connect(tmp_path / "w.duckdb")
    client = make_client(httpx.MockTransport(handler))
    results = pipeline.ingest([broken, daily_series], con, client, tmp_path, clock=clock)

    assert [r.status for r in results] == ["failed", "success"]
    logged = con.execute(
        "SELECT series_key, status, message FROM raw.run_log ORDER BY 1"
    ).fetchall()
    assert logged[0][:2] == ("policy_rate", "failed") and "404" in logged[0][2]


def test_landed_file_is_byte_identical_to_response(
    tmp_path, daily_series, valet_client, fixture_bytes
):
    con = warehouse.connect(tmp_path / "w.duckdb")
    pipeline.ingest([daily_series], con, valet_client, tmp_path, clock=clock)
    landed = next((tmp_path / "raw" / "valet" / "usd_cad").glob("*.json"))
    assert landed.read_bytes() == fixture_bytes("valet_observations.json")
    assert json.loads(landed.read_bytes())["observations"]
