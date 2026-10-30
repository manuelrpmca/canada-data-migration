from datetime import date

import httpx
import pytest

from cdm.http import make_client
from cdm.sources import Observation, statcan, valet


def test_valet_parse_recorded_response(fixture_bytes):
    observations = valet.parse_observations(fixture_bytes("valet_observations.json"), "FXUSDCAD")
    assert observations == [
        Observation(date(2026, 10, 15), 1.4196),
        Observation(date(2026, 10, 16), 1.4154),
        Observation(date(2026, 10, 19), 1.4097),
        Observation(date(2026, 10, 20), 1.4054),
    ]


def test_valet_parse_skips_empty_values():
    # Synthetic payload: the recorded responses have no empty cells, but Valet documents them.
    raw = b"""{"observations": [{"d": "2026-01-02", "FXUSDCAD": {"v": "1.5"}},
        {"d": "2026-01-05", "FXUSDCAD": {"v": ""}}, {"d": "2026-01-06"}]}"""
    assert valet.parse_observations(raw, "FXUSDCAD") == [Observation(date(2026, 1, 2), 1.5)]


def test_valet_fetch_sends_start_date(fixture_bytes):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, content=fixture_bytes("valet_observations.json"))

    result = valet.fetch_observations(
        make_client(httpx.MockTransport(handler)), "FXUSDCAD", date(2026, 10, 15)
    )
    assert seen["url"].endswith("/valet/observations/FXUSDCAD/json?start_date=2026-10-15")
    assert len(result.observations) == 4
    assert result.raw == fixture_bytes("valet_observations.json")


def test_statcan_parse_recorded_response(fixture_bytes):
    observations = statcan.parse_observations(fixture_bytes("statcan_vector_data.json"))
    assert observations == [
        Observation(date(2026, 5, 1), 170.2),
        Observation(date(2026, 6, 1), 169.3),
        Observation(date(2026, 7, 1), 169.9),
    ]


def test_statcan_parse_skips_null_values():
    # Synthetic payload: the recorded responses have no suppressed values, but WDS documents them.
    raw = b"""[{"status": "SUCCESS", "object": {"vectorDataPoint": [
        {"refPer": "2026-01-01", "value": 1.5}, {"refPer": "2026-02-01", "value": null}]}}]"""
    assert statcan.parse_observations(raw) == [Observation(date(2026, 1, 1), 1.5)]


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
        make_client(httpx.MockTransport(handler)),
        "41691919",
        date(2026, 6, 1),
        today=date(2026, 7, 10),
    )
    assert seen["body"] == b'[{"vectorId":41691919,"latestN":2}]'
    assert [o.ref_date for o in result.observations] == [date(2026, 6, 1), date(2026, 7, 1)]


@pytest.mark.parametrize(
    ("coordinate", "expected"),
    [
        ("14.2", "14.2.0.0.0.0.0.0.0.0"),
        ("7.7.1.1.1.1.", "7.7.1.1.1.1.0.0.0.0"),
        ("1.2.0.0.0.0.0.0.0.0", "1.2.0.0.0.0.0.0.0.0"),
    ],
)
def test_pad_coordinate(coordinate, expected):
    assert statcan.pad_coordinate(coordinate) == expected


def test_pad_coordinate_rejects_too_many_positions():
    with pytest.raises(ValueError):
        statcan.pad_coordinate("1.1.1.1.1.1.1.1.1.1.1")


def test_find_vector_sends_padded_coordinate():
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, json=[{"status": "SUCCESS", "object": {"vectorId": 41691919}}])

    statcan.find_vector(make_client(httpx.MockTransport(handler)), 18100004, "14.2")
    assert seen["body"] == b'[{"productId":18100004,"coordinate":"14.2.0.0.0.0.0.0.0.0"}]'
