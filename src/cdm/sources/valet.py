"""Bank of Canada Valet API client. No key needed. Docs: https://www.bankofcanada.ca/valet-api-how-to/"""

from __future__ import annotations

import json
from datetime import date

import httpx

from cdm.http import request_with_retry
from cdm.sources import FetchResult, Observation

BASE_URL = "https://www.bankofcanada.ca/valet"


def fetch_observations(client: httpx.Client, series_id: str, start: date) -> FetchResult:
    url = f"{BASE_URL}/observations/{series_id}/json"
    response = request_with_retry(client, "GET", url, params={"start_date": start.isoformat()})
    return FetchResult(
        url=str(response.url),
        raw=response.content,
        observations=parse_observations(response.content, series_id),
    )


def parse_observations(raw: bytes, series_id: str) -> list[Observation]:
    """Parse `{"observations": [{"d": "YYYY-MM-DD", "<series>": {"v": "1.23"}}, ...]}`.

    Dates with no value for the series (holidays, gaps) are skipped, not loaded as nulls.
    """
    payload = json.loads(raw)
    observations = []
    for row in payload.get("observations", []):
        cell = row.get(series_id)
        if not cell or cell.get("v") in (None, ""):
            continue
        observations.append(Observation(date.fromisoformat(row["d"]), float(cell["v"])))
    return observations


def describe_series(client: httpx.Client, series_id: str) -> dict:
    """Return the series' metadata (label, description) to confirm the identifier is right."""
    response = request_with_retry(client, "GET", f"{BASE_URL}/series/{series_id}/json")
    return response.json()
