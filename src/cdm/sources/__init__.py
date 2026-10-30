"""One API client per source. Each returns the raw response bytes and the parsed observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Observation:
    ref_date: date
    value: float


@dataclass(frozen=True)
class FetchResult:
    url: str
    raw: bytes
    observations: list[Observation]
