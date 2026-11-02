from pathlib import Path

import pytest

from cdm import settings
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


def test_project_root_found_from_a_subfolder(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "series.yml").write_text("series: []\n", encoding="utf-8")
    (tmp_path / "dbt").mkdir()
    monkeypatch.delenv("CDM_ROOT", raising=False)
    monkeypatch.chdir(tmp_path / "dbt")
    assert settings.project_root() == tmp_path


def test_cdm_root_overrides_the_search(tmp_path, monkeypatch):
    monkeypatch.setenv("CDM_ROOT", str(tmp_path))
    assert settings.project_root() == tmp_path
