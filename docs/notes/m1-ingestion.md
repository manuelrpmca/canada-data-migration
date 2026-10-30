# M1. Ingestion

Date closed: open · Owner hours: to be logged

## What was done

- Python project with uv, a lock file, ruff and pytest ([ADR 0004](../decisions/0004-python-toolchain.md)). Dependabot watches the Python dependencies and GitHub Actions.
- `config/series.yml` lists the four v0.1 series ([ADR 0003](../decisions/0003-data-sources.md)).
- One client per source: `src/cdm/sources/valet.py` and `statcan.py`. They share one HTTP helper with timeouts and retries.
- Raw landing, DuckDB upsert, lookback window and run log ([ADR 0005](../decisions/0005-ingestion-pattern.md)).
- CLI commands: `cdm ingest`, `cdm status`, `cdm verify` and `cdm find-vector`.
- Unit tests that never call the network.

## Why it was done this way

- **Retries with back-off and jitter, written by hand** (`src/cdm/http.py`, about 30 lines). Both APIs ask clients to back off, and StatCan answers HTTP 409 while it publishes. A short, tested function is easier to explain than a retry library's settings.
- **Explicit UPDATE + INSERT in one transaction**, not a single `INSERT ... ON CONFLICT`. The same comparison produces the inserted, updated and unchanged counts and changes the data, so the run log cannot disagree with the table. It is also the shape of the Oracle `MERGE` in M4.
- **The table key is `(source, series_key, ref_date)`.** ADR 0005 named `series_id`. The stable key from the config is used instead, because a StatCan vector ID is not known until it is verified, and the vector ID is still stored in its own column.
- **StatCan uses `getDataFromVectorsAndLatestNPeriods`.** It asks for the number of months since the request start. The WDS guide is inconsistent about the parameter names of the date-range method, so this documented method avoids guessing.
- **A series without an identifier is skipped and logged, not guessed.**

## Measured results

To be filled from a real run: rows per series, first and last date, and the second-run counts (step 6 of the QA script).

## What I would say in an interview

"The ingestion is incremental and idempotent. Each run re-reads a short window before the last loaded date, so statistical revisions are picked up. It saves the raw response before parsing, so any load can be replayed. Then it merges on a natural key and logs inserted, updated and unchanged counts per series. Running it twice changes nothing, and a test proves it."

## What I learned / what surprised me

- To be filled in by Manuel at milestone close.
