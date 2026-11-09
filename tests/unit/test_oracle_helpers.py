"""Offline checks of the Oracle loader helpers and SQL scripts (no database needed)."""

from __future__ import annotations

import re
import subprocess
from datetime import date, datetime

import pytest

from cdm import container
from cdm.load import oracle
from cdm.settings import Series

SCRIPTS = ("ddl/01_accounts.sql", *oracle.OWNER_SCRIPTS)
REPLACEMENTS = {"p": "CDM", "loader_password": "Aa1", "migration_password": "Bb2"}


def test_split_script_uses_slash_lines_and_drops_comment_only_chunks():
    text = "-- header\nSELECT 1 FROM dual\n/\n-- only a comment\n/\nBEGIN\n  NULL;\nEND;\n/\n"
    assert oracle.split_script(text) == ["-- header\nSELECT 1 FROM dual", "BEGIN\n  NULL;\nEND;"]


@pytest.mark.parametrize("name", SCRIPTS)
def test_scripts_render_completely(name):
    text = oracle.render((oracle.oracle_dir() / name).read_text(encoding="utf-8"), REPLACEMENTS)
    assert not re.search(r"\{(p|loader_password|migration_password)\}", text)
    statements = oracle.split_script(text)
    assert statements
    # A plain SQL statement must not end with ";" (Oracle rejects it); PL/SQL blocks must.
    for statement in statements:
        code = "\n".join(ln for ln in statement.splitlines() if not ln.startswith("--"))
        plsql = re.match(r"(CREATE OR REPLACE (PACKAGE|PROCEDURE|FUNCTION)|BEGIN)", code)
        assert statement.endswith(";") == bool(plsql), statement[:60]


def test_ensure_passwords_fills_only_missing_keys(tmp_path, monkeypatch):
    for key in oracle.PASSWORD_KEYS:
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text("GCP_PROJECT_ID=demo\nORACLE_PASSWORD=Keep1\nORACLE_LOADER_PASSWORD=\n")

    filled = oracle.ensure_passwords(env)

    values = oracle.read_env_file(env)
    assert filled == ["ORACLE_LOADER_PASSWORD", "ORACLE_MIGRATION_PASSWORD"]
    assert values["ORACLE_PASSWORD"] == "Keep1" and values["GCP_PROJECT_ID"] == "demo"
    assert re.fullmatch(r"[A-Za-z][A-Za-z0-9]{23}", values["ORACLE_LOADER_PASSWORD"])
    assert oracle.ensure_passwords(env) == []  # second run changes nothing


def test_load_settings_says_what_to_run_when_passwords_are_missing(tmp_path, monkeypatch):
    for key in oracle.PASSWORD_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CDM_ROOT", str(tmp_path))
    with pytest.raises(oracle.OracleConfigError, match="cdm oracle up"):
        oracle.load_settings()


def test_landed_runs_are_oldest_first_and_carry_the_fetch_time(tmp_path, daily_series: Series):
    folder = tmp_path / "raw" / "valet" / daily_series.key
    folder.mkdir(parents=True)
    for name in ("20261102T150012Z-bbbbbb", "20261101T150010Z-aaaaaa", "notes"):
        (folder / f"{name}.json").write_text("{}")

    runs = oracle.landed_runs(tmp_path, daily_series)

    assert [r.run_id for r in runs] == ["20261101T150010Z-aaaaaa", "20261102T150012Z-bbbbbb"]
    assert runs[0].received_at == datetime(2026, 11, 1, 15, 0, 10)


def test_compare_flags_any_difference():
    same = oracle.SeriesProfile(3, date(2026, 1, 1), date(2026, 3, 1), 6.0000001)
    other = oracle.SeriesProfile(3, date(2026, 1, 1), date(2026, 3, 1), 6.1)
    result = oracle.compare({"a": same, "b": same}, {"a": same, "b": other, "c": same})
    assert [(key, verdict) for key, _, _, verdict in result] == [
        ("a", "match"), ("b", "MISMATCH"), ("c", "MISMATCH"),
    ]  # fmt: skip


def test_missing_docker_says_how_to_install(monkeypatch):
    monkeypatch.setattr(container.shutil, "which", lambda _: None)
    with pytest.raises(container.DockerError, match="docker.io docker-compose-v2"):
        container.check_docker()


def _fake_docker_info(returncode, stderr):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], returncode, stdout="", stderr=stderr)

    return run


def test_docker_permission_denied_says_how_to_join_group(monkeypatch):
    monkeypatch.setattr(container.shutil, "which", lambda _: "/usr/bin/docker")
    stderr = "permission denied while trying to connect to the Docker daemon socket"
    monkeypatch.setattr(container.subprocess, "run", _fake_docker_info(1, stderr))
    with pytest.raises(container.DockerError, match="usermod -aG docker"):
        container.check_docker()


def test_docker_not_running_says_how_to_start(monkeypatch):
    monkeypatch.setattr(container.shutil, "which", lambda _: "/usr/bin/docker")
    stderr = "Cannot connect to the Docker daemon. Is the docker daemon running?"
    monkeypatch.setattr(container.subprocess, "run", _fake_docker_info(1, stderr))
    with pytest.raises(container.DockerError, match="systemctl start docker"):
        container.check_docker()
