from datetime import date

import httpx
import pytest

from cdm.http import make_client
from cdm.sources import Observation, statcan, valet


def test_valet_parse_skips_empty_values(fixture_bytes):
    observations = valet.parse_observations(fixture_bytes("valet_observations.json"), "FXUSDCAD")
    assert observations == [
        Observation(date(2026, 1, 2), 1.1),
        Observation(date(2026, 1, 5), 1.2),
        Observation(date(2026, 1, 7), 1.3),
    ]


def test_valet_fetch_sends_start_date(fixture_bytes):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, content=fixture_bytes("valet_observations.json"))

    result = valet.fetch_observations(
        make_client(httpx.MockTransport(handler)), "FXUSDCAD", date(2026, 1, 1)
    )
    assert seen["url"].endswith("/valet/observations/FXUSDCAD/json?start_date=2026-01-01")
    assert len(result.observations) == 3
    assert result.raw == fixture_bytes("valet_observations.json")


def test_statcan_parse_skips_null_values(fixture_bytes):
    observations = statcan.parse_observations(fixture_bytes("statcan_vector_data.json"))
    assert observations == [
        Observation(date(2025, 11, 1), 100.0),
        Observation(date(2025, 12, 1), 101.0),
    ]


def test_statcan_failed_status_raises():
    with pytest.raises(statcan.WdsError):
        statcan.parse_observations(b'[{"status": "FAILED", "object": "Invalid vector"}]')


@pytest.mark.parametrize(
    ("start", "today", "expected"),
    [
        (date(2026, 1, 1), date(2026, 1, 31), 1),
        (date(2025, 11, 1), date(2026, 1, 15), 3),
        (date(2017, 1, 1), date(2026, 10, 29), 118),
    ],
)
def test_months_since(start, today, expected):
    assert statcan.months_since(start, today) == expected


def test_statcan_fetch_requests_enough_periods_and_filters_start(fixture_bytes):
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, content=fixture_bytes("statcan_vector_data.json"))

    result = statcan.fetch_observations(
        make_client(httpx.MockTransport(handler)), "1", date(2025, 12, 1), today=date(2026, 2, 10)
    )
    assert seen["body"] == b'[{"vectorId":1,"latestN":3}]'
    assert [o.ref_date for o in result.observations] == [date(2025, 12, 1)]
