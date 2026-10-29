# 0004. Python toolchain

- Status: Accepted
- Date: 2026-10-29
- Milestone: M1

## Context

Ingestion, loading and reconciliation are written in Python. The environment must be identical on the owner's machine and in CI, installable with one command, and simple enough to explain in an interview.

## Options considered

1. **pip + venv + requirements.txt.** Universal, but locking exact versions needs extra tooling (pip-tools) and setup is several commands.
2. **Poetry.** Mature lock file, but slower and heavier than needed here.
3. **uv** with `pyproject.toml` and `uv.lock`. Manages the Python version, the virtual environment and an exact lock file in one tool; `uv sync` reproduces the environment; widely used in new Python projects.

## Decision

- **Python 3.12**, pinned in `pyproject.toml` (`requires-python`) and in `.python-version`.
- **uv** for environments and locking; `uv.lock` is committed.
- **ruff** for linting and formatting (one tool instead of flake8 + isort + black).
- **pytest** for tests; tests use recorded API responses in `tests/fixtures/` and never call the network.
- **httpx** as the HTTP client (explicit timeouts, clean API). Retries with exponential back-off and jitter are written in a small, tested helper rather than pulled from a library, so the behaviour is visible and explainable.
- A single CLI entry point, `uv run cdm <command>`, so the same commands work on macOS, Linux and Windows without `make`.

Exact package versions are pinned when `pyproject.toml` is created in M1, not in this ADR.

## Consequences

- One install step: `uv sync`. Contributors need uv installed (one command on every OS).
- CI uses the same lock file, so "works on my machine" and "works in CI" mean the same thing.
- If uv ever becomes a problem, `pyproject.toml` stays standard and can be installed with pip.
