"""Run the dbt project in dbt/ against the DuckDB warehouse (ADR 0007).

dbt is called in-process through its Python API, so `uv run cdm run` needs no shell, `make`
or PATH changes on Windows. The warehouse path reaches dbt/profiles.yml through the
CDM_DUCKDB_PATH environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

from cdm import settings


def dbt_dir() -> Path:
    return settings.project_root() / "dbt"


def build(db_path: Path, args: list[str] | None = None) -> bool:
    """`dbt build` (models, seeds, tests). Returns True when every node passed."""
    from dbt.cli.main import dbtRunner  # imported here: dbt is slow to import

    os.environ["CDM_DUCKDB_PATH"] = str(db_path.resolve())
    project = str(dbt_dir())
    result = dbtRunner().invoke(
        ["build", "--project-dir", project, "--profiles-dir", project, *(args or [])]
    )
    return bool(result.success)
