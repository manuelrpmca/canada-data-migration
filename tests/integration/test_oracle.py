"""The governed Oracle source against a real Oracle Database Free (ADR 0009).

Runs only when CDM_ORACLE_TESTS=1 and Oracle is up (`uv run cdm oracle up`), locally or in the
`oracle` CI job. The tests build their own accounts with the prefix CDMTEST (CDMTEST_OWNER,
CDMTEST_LOADER, CDMTEST_MIGRATION) and drop them at the end, so they never touch CDM_* data.
The payloads are the recorded fixtures, plus edited copies to simulate a revision.
The tests share one database and run in file order: each builds on the loads before it.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime

import pytest

from cdm.load import oracle
from cdm.settings import Series
from cdm.sources import statcan, valet

pytestmark = [
    pytest.mark.oracle,
    pytest.mark.skipif(
        os.environ.get("CDM_ORACLE_TESTS") != "1",
        reason="needs Oracle: run `uv run cdm oracle up`, then set CDM_ORACLE_TESTS=1",
    ),
]

USD = Series("t_usd_cad", "valet", "FXUSDCAD", "USD/CAD", "CAD per USD", "daily",
             date(2026, 1, 1), 14, True)  # fmt: skip
CPI = Series("t_cpi", "statcan", "41691919", "CPI", "index", "monthly",
             date(2026, 1, 1), 3, True, 18100004)  # fmt: skip
RUN_1 = "20261101T150000Z-aaaaaa"
RUN_2 = "20261102T150000Z-bbbbbb"


@pytest.fixture(scope="module")
def cfg():
    base = oracle.load_settings()
    cfg = oracle.OracleSettings(
        dsn=base.dsn,
        system_password=base.system_password,
        loader_password=oracle.new_password(),
        migration_password=oracle.new_password(),
        prefix="CDMTEST",
    )
    oracle.drop_accounts(cfg)
    oracle.setup(cfg)
    yield cfg
    oracle.drop_accounts(cfg)


@pytest.fixture
def loader(cfg):
    with oracle.connect_loader(cfg) as con:
        yield con


@pytest.fixture
def reader(cfg):
    with oracle.connect_migration(cfg) as con:
        yield con


def land(data_dir, series: Series, run_id: str, raw: bytes) -> None:
    folder = data_dir / "raw" / series.source / series.key
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{run_id}.json").write_bytes(raw)


def revised_valet(raw: bytes) -> bytes:
    """Second response: the first day's value revised, one new day appended."""
    payload = json.loads(raw)
    payload["observations"][0]["FXUSDCAD"]["v"] = "1.5000"
    payload["observations"].append({"d": "2026-10-30", "FXUSDCAD": {"v": "1.3999"}})
    return json.dumps(payload).encode()


def rows(con, sql: str, params=None) -> list[tuple]:
    with con.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()


def test_setup_runs_again_without_changes(cfg):
    oracle.setup(cfg)  # second run: every statement is create-if-missing or replace


def test_first_load_matches_the_python_parsers(cfg, loader, reader, tmp_path, fixture_bytes):
    usd_raw = fixture_bytes("valet_observations.json")
    cpi_raw = fixture_bytes("statcan_vector_data.json")
    land(tmp_path, USD, RUN_1, usd_raw)
    land(tmp_path, CPI, RUN_1, cpi_raw)

    results = {r.series_key: r for r in oracle.load(loader, cfg.owner, [USD, CPI], tmp_path)}

    expected = {
        USD.key: {o.ref_date: o.value for o in valet.parse_observations(usd_raw, "FXUSDCAD")},
        CPI.key: {o.ref_date: o.value for o in statcan.parse_observations(cpi_raw)},
    }
    for key, values in expected.items():
        assert results[key].loaded == 1 and results[key].inserted == len(values)
        current = rows(reader, "SELECT ref_date, value FROM observation_current "
                               "WHERE series_key = :k", {"k": key})  # fmt: skip
        assert {d.date(): float(v) for d, v in current} == values


def test_reload_changes_nothing(cfg, loader, reader, tmp_path, fixture_bytes):
    land(tmp_path, USD, RUN_1, fixture_bytes("valet_observations.json"))
    before = rows(reader, "SELECT COUNT(*) FROM observation_revision")
    [result] = oracle.load(loader, cfg.owner, [USD], tmp_path)
    assert (result.already, result.loaded) == (1, 0)
    assert rows(reader, "SELECT COUNT(*) FROM observation_revision") == before


def test_revision_keeps_what_was_known_before(cfg, loader, reader, tmp_path, fixture_bytes):
    raw = fixture_bytes("valet_observations.json")
    land(tmp_path, USD, RUN_1, raw)
    land(tmp_path, USD, RUN_2, revised_valet(raw))
    first_day = valet.parse_observations(raw, "FXUSDCAD")[0]

    [result] = oracle.load(loader, cfg.owner, [USD], tmp_path)
    assert (result.loaded, result.inserted, result.revised) == (1, 1, 1)

    history = rows(
        reader,
        "SELECT value, known_from, known_to FROM observation_revision "
        "WHERE series_key = :k AND ref_date = :d ORDER BY known_from",
        {"k": USD.key, "d": first_day.ref_date},
    )
    assert [float(v) for v, _, _ in history] == [first_day.value, 1.5]
    assert history[0][2] == history[1][1] == datetime(2026, 11, 2, 15, 0)  # closed when revised
    assert history[1][2] is None

    def as_of(moment: str) -> float:
        [(value,)] = rows(
            reader,
            f"SELECT value FROM observation_as_of(TIMESTAMP '{moment}') "
            "WHERE series_key = :k AND ref_date = :d",
            {"k": USD.key, "d": first_day.ref_date},
        )
        return float(value)

    assert as_of("2026-11-01 18:00:00") == first_day.value
    assert as_of("2026-11-02 18:00:00") == 1.5
    assert rows(reader, "SELECT COUNT(*) FROM observation_as_of(TIMESTAMP '2026-10-31 00:00:00') "
                        "WHERE series_key = :k", {"k": USD.key}) == [(0,)]  # fmt: skip


def test_out_of_order_file_is_refused_and_audited(cfg, loader, reader, tmp_path, fixture_bytes):
    before = rows(reader, "SELECT COUNT(*) FROM observation_revision")
    land(tmp_path, USD, "20261031T150000Z-cccccc", fixture_bytes("valet_observations.json"))
    [result] = oracle.load(loader, cfg.owner, [USD], tmp_path)
    assert result.failed == 1 and "Out of order" in result.message
    assert rows(reader, "SELECT COUNT(*) FROM observation_revision") == before
    assert rows(
        reader,
        "SELECT status FROM load_audit WHERE run_id = '20261031T150000Z-cccccc'",
    ) == [("failed",)]


def test_failed_wds_response_is_refused(cfg, loader, reader, tmp_path):
    land(tmp_path, CPI, RUN_2, b'[{"status": "FAILED", "object": "Vector not found"}]')
    [result] = oracle.load(loader, cfg.owner, [CPI], tmp_path)
    assert result.failed == 1 and "SUCCESS" in result.message
    assert rows(reader, "SELECT COUNT(*) FROM landed_file WHERE run_id = :r AND series_key = :k",
                {"r": RUN_2, "k": CPI.key}) == [(0,)]  # fmt: skip


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO source_system VALUES ('x', 'x', 'x')",
        "UPDATE observation_revision SET value = 0",
        "DELETE FROM load_audit",
        "BEGIN cdm_load.sync_series('x', 'valet', 'x', NULL, 'x', 'x', 'daily', SYSDATE); END;",
    ],
)
def test_migration_user_is_read_only(reader, statement):
    with pytest.raises(oracle.oracledb.DatabaseError) as error:
        rows(reader, statement)
    assert any(code in str(error.value) for code in ("ORA-41900", "ORA-01031", "PLS-00201"))


def test_loader_cannot_touch_tables_directly(cfg, loader):
    for statement in (
        f"SELECT COUNT(*) FROM {cfg.owner}.observation_revision",
        f"DELETE FROM {cfg.owner}.load_audit",
    ):
        with pytest.raises(oracle.oracledb.DatabaseError, match="ORA-00942|ORA-41900|ORA-01031"):
            rows(loader, statement)


def test_every_column_is_described_and_classified(cfg):
    with oracle.connect_system(cfg) as con:
        catalog = rows(
            con,
            "SELECT COUNT(*) FROM all_tab_columns c JOIN all_tables t "
            "ON t.owner = c.owner AND t.table_name = c.table_name AND t.temporary = 'N' "
            "WHERE c.owner = :o",
            {"o": cfg.owner},
        )
    with oracle.connect_migration(cfg) as reader:
        dictionary = rows(reader, "SELECT COUNT(*) FROM data_dictionary")
        gaps = rows(
            reader,
            "SELECT table_name, column_name FROM data_dictionary "
            "WHERE column_description IS NULL OR table_description IS NULL "
            "OR column_classification NOT IN ('Public', 'Internal') "
            "OR table_classification NOT IN ('Public', 'Internal')",
        )
    assert dictionary == catalog
    assert gaps == []
