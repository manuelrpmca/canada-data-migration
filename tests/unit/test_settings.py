from pathlib import Path

import pytest

from cdm.settings import load_series

REPO_CONFIG = Path(__file__).parents[2] / "config" / "series.yml"


def test_repo_config_loads_four_series():
    series = load_series(REPO_CONFIG)
    assert [s.key for s in series] == [
        "usd_cad", "policy_rate", "cpi_ontario", "unemployment_ontario",
    ]  # fmt: skip


def test_unknown_source_is_rejected(tmp_path):
    bad = tmp_path / "series.yml"
    bad.write_text(
        "series:\n  - {key: x, source: fred, series_id: A, name: n, unit: u,"
        " frequency: daily, start_date: '2020-01-01', lookback: 1}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown source"):
        load_series(bad)
