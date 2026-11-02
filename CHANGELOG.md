# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

Planned as `0.1.0`; the version and date are set in the release pull request after the owner's M3 QA run.

### Added

- CI (`.github/workflows/ci.yml`) on every pull request and push to `main`, on `ubuntu-latest` and `windows-latest`, in PowerShell: locked install, ruff lint and format, pytest (including `dbt build` on a synthetic warehouse) and a CLI smoke test. Actions pinned to commit SHAs, read-only permissions.
- Daily run (`.github/workflows/daily.yml`) at 15:00 UTC and on demand: `cdm run` against the live APIs, source freshness, a summary table, and the warehouse, landing files and dbt logs as an artifact. The warehouse is kept in the Actions cache so runs are incremental. Changes to the workflow are tested on the pull request, including a clean-checkout run on Windows.
- README for v0.1: CI and daily badges, architecture, one-command run, results from real runs, decisions, limits and next steps.
- QA script for M3 and the M3 note.

- `cdm dbt <command>` runs any dbt command on the project and warehouse from any folder (for example `uv run cdm dbt docs serve`); QA scripts no longer `cd dbt`.
- M2 dbt models: dbt Core project in `dbt/` on DuckDB with per-series source freshness, staging views, star schema (`dim_date`, `dim_indicator`, `fct_observation`) and `mart_monthly_indicators`, 57 data tests and a unit test, and a `source_publishers` seed with attribution text.
- `cdm run` (ingest + `dbt build`) and `cdm sql` (one statement, for QA). `cdm ingest` writes `raw.series` from `config/series.yml`.
- Offline integration test that runs `dbt build` on a synthetic warehouse.
- QA script for M2 in PowerShell.
- M1 ingestion: `cdm` CLI (`ingest`, `status`, `verify`, `find-vector`), Bank of Canada Valet and Statistics Canada WDS clients with retries and back-off, raw landing, idempotent DuckDB upsert with lookback window, run log, unit tests, Dependabot config.
- QA script for M1 rewritten for PowerShell on Windows 11.
- Series identifiers verified against the live APIs; StatCan vector IDs set (CPI Ontario 41691919, unemployment rate Ontario 2063949). First real ingest results in the M1 note.

### Changed

- Failed series explain the likely cause in one line: HTTP 403 points to a VPN or company network, a connection error to the network or proxy.
- A missing warehouse is reported with the command that creates it (`uv run cdm run`), and `cdm dbt` no longer creates an empty warehouse file.

- QA scripts are Windows-first: rules and troubleshooting in `docs/qa/README.md`; every script has a one-time setup (uv install, PATH for the current window, clone) and starts with `cd $HOME\canada-data-migration`; M0 and M3 snippets moved from bash to PowerShell.
- Test fixtures are now trimmed responses recorded from the live APIs, not hand-written.

### Fixed

- `cdm dbt --version` and other dbt options right after `cdm dbt` were rejected by the `cdm` argument parser; everything after `dbt` now goes to dbt unchanged (found by the new CI smoke test).

- `cdm` finds the repository root from any subfolder (for example `dbt\`), instead of failing with `FileNotFoundError` on `config\series.yml`.
- `cdm find-vector` pads the coordinate to the 10 positions WDS requires (a shorter one returned HTTP 406).

- Project plan for Phase 0 and Phase 1: repository structure, ADRs 0001-0009, milestone plan with QA scripts, progress tracker and milestone note for M0.
- MIT license, `.gitignore`, `.env.example` with empty keys, `MEMORY.md`.
- README with "work in progress" status, planned architecture diagram and data attribution.
