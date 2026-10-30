"""Statistics Canada Web Data Service (WDS) client.

Docs: https://www.statcan.gc.ca/en/developers/wds/user-guide
Limits: 25 requests per second per IP. Data is released at 8:30 a.m. Eastern; before that some
tables answer HTTP 409, which the HTTP helper retries.
"""

from __future__ import annotations

import json
from datetime import date

import httpx

from cdm.http import request_with_retry
from cdm.sources import FetchResult, Observation

BASE_URL = "https://www150.statcan.gc.ca/t1/wds/rest"
COORDINATE_POSITIONS = 10


class WdsError(RuntimeError):
    """WDS answered HTTP 200 but reported a failure in the body."""


def months_since(start: date, today: date) -> int:
    """Number of monthly periods from `start` to `today`, both included."""
    return (today.year - start.year) * 12 + (today.month - start.month) + 1


def fetch_observations(
    client: httpx.Client, vector_id: str, start: date, today: date | None = None
) -> FetchResult:
    """Fetch every monthly period from `start` to today with getDataFromVectorsAndLatestNPeriods."""
    latest_n = max(1, months_since(start, today or date.today()))
    url = f"{BASE_URL}/getDataFromVectorsAndLatestNPeriods"
    response = request_with_retry(
        client, "POST", url, json=[{"vectorId": int(vector_id), "latestN": latest_n}]
    )
    observations = [o for o in parse_observations(response.content) if o.ref_date >= start]
    return FetchResult(url=url, raw=response.content, observations=observations)


def parse_observations(raw: bytes) -> list[Observation]:
    """Parse `[{"status": "SUCCESS", "object": {"vectorDataPoint": [{"refPer", "value"}]}}]`.

    Suppressed or missing values (value null) are skipped.
    """
    payload = json.loads(raw)
    observations = []
    for item in payload:
        if item.get("status") != "SUCCESS":
            raise WdsError(f"WDS returned status {item.get('status')!r}: {item.get('object')}")
        for point in item["object"].get("vectorDataPoint", []):
            if point.get("value") is None:
                continue
            observations.append(
                Observation(date.fromisoformat(point["refPer"][:10]), float(point["value"]))
            )
    return observations


def describe_vector(client: httpx.Client, vector_id: str) -> dict:
    """Series metadata for a vector (title, product ID, frequency)."""
    url = f"{BASE_URL}/getSeriesInfoFromVector"
    response = request_with_retry(client, "POST", url, json=[{"vectorId": int(vector_id)}])
    return response.json()


def describe_cube(client: httpx.Client, product_id: int) -> dict:
    """Table metadata: title and dimensions with their members, to find a coordinate."""
    url = f"{BASE_URL}/getCubeMetadata"
    response = request_with_retry(client, "POST", url, json=[{"productId": int(product_id)}])
    return response.json()


def pad_coordinate(coordinate: str) -> str:
    """Pad to the 10 positions WDS needs: "14.2" -> "14.2.0.0.0.0.0.0.0.0".

    A shorter coordinate is answered with HTTP 406 (seen live on 2026-10-30).
    """
    parts = coordinate.strip(".").split(".")
    if len(parts) > COORDINATE_POSITIONS:
        raise ValueError(f"coordinate has more than {COORDINATE_POSITIONS} positions: {coordinate}")
    return ".".join(parts + ["0"] * (COORDINATE_POSITIONS - len(parts)))


def find_vector(client: httpx.Client, product_id: int, coordinate: str) -> dict:
    """Series metadata (including vectorId) for one coordinate of a table."""
    url = f"{BASE_URL}/getSeriesInfoFromCubePidCoord"
    response = request_with_retry(
        client,
        "POST",
        url,
        json=[{"productId": int(product_id), "coordinate": pad_coordinate(coordinate)}],
    )
    return response.json()
