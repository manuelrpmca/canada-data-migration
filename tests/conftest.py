from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from cdm.settings import Series

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_bytes():
    return lambda name: (FIXTURES / name).read_bytes()


@pytest.fixture
def daily_series() -> Series:
    return Series(
        key="usd_cad", source="valet", series_id="FXUSDCAD", name="USD/CAD",
        unit="CAD per USD", frequency="daily", start_date=date(2026, 1, 1), lookback=14,
    )  # fmt: skip


@pytest.fixture
def monthly_series() -> Series:
    return Series(
        key="cpi_ontario", source="statcan", series_id="1", name="CPI",
        unit="index", frequency="monthly", start_date=date(2025, 1, 1), lookback=3,
    )  # fmt: skip
