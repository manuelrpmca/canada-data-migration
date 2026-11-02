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
    return run(db_path, ["build", *(args or [])])


def run(db_path: Path, args: list[str]) -> bool:
    """Any dbt command (for example ["source", "freshness"]) on this project and warehouse,
    whatever the current folder. Returns True when dbt reports success."""
    from dbt.cli.main import dbtRunner  # imported here: dbt is slow to import

    if not args:
        args = ["--help"]
    os.environ["CDM_DUCKDB_PATH"] = str(db_path.resolve())
    project = str(dbt_dir())
    if args[0] in ("--help", "-h", "--version"):
        result = dbtRunner().invoke(args)
    else:
        result = dbtRunner().invoke([*args, "--project-dir", project, "--profiles-dir", project])
    return bool(result.success)
