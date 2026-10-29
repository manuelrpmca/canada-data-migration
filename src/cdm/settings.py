"""Configuration: the series list (config/series.yml) and paths from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

SOURCES = ("valet", "statcan")
FREQUENCIES = ("daily", "monthly")


@dataclass(frozen=True)
class Series:
    key: str
    source: str
    series_id: str | None
    name: str
    unit: str
    frequency: str
    start_date: date
    lookback: int
    verified: bool = False
    product_id: int | None = None

    @property
    def ready(self) -> bool:
        """A series can be ingested only once it has an identifier."""
        return bool(self.series_id)


def project_root() -> Path:
    return Path(os.environ.get("CDM_ROOT", Path.cwd()))


def data_dir() -> Path:
    return Path(os.environ.get("CDM_DATA_DIR", project_root() / "data"))


def default_db_path() -> Path:
    return data_dir() / "warehouse.duckdb"


def load_series(path: Path | None = None) -> list[Series]:
    path = path or project_root() / "config" / "series.yml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    series = [_parse(item) for item in raw["series"]]
    keys = [s.key for s in series]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate series keys in {path}")
    return series


def _parse(item: dict) -> Series:
    source = item["source"]
    frequency = item["frequency"]
    if source not in SOURCES:
        raise ValueError(f"{item['key']}: unknown source {source!r}")
    if frequency not in FREQUENCIES:
        raise ValueError(f"{item['key']}: unknown frequency {frequency!r}")
    series_id = item.get("series_id")
    return Series(
        key=item["key"],
        source=source,
        series_id=str(series_id) if series_id is not None else None,
        name=item["name"],
        unit=item["unit"],
        frequency=frequency,
        start_date=date.fromisoformat(str(item["start_date"])),
        lookback=int(item["lookback"]),
        verified=bool(item.get("verified", False)),
        product_id=item.get("product_id"),
    )
