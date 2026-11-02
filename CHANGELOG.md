# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `cdm dbt <command>` runs any dbt command on the project and warehouse from any folder (for example `uv run cdm dbt docs serve`); QA scripts no longer `cd dbt`.
- M2 dbt models: dbt Core project in `dbt/` on DuckDB with per-series source freshness, staging views, star schema (`dim_date`, `dim_indicator`, `fct_observation`) and `mart_monthly_indicators`, 57 data tests and a unit test, and a `source_publishers` seed with attribution text.
- `cdm run` (ingest + `dbt build`) and `cdm sql` (one statement, for QA). `cdm ingest` writes `raw.series` from `config/series.yml`.
- Offline integration test that runs `dbt build` on a synthetic warehouse.
- QA script for M2 in PowerShell.
- M1 ingestion: `cdm` CLI (`ingest`, `status`, `verify`, `find-vector`), Bank of Canada Valet and Statistics Canada WDS clients with retries and back-off, raw landing, idempotent DuckDB upsert with lookback window, run log, unit tests, Dependabot config.
- QA script for M1 rewritten for PowerShell on Windows 11.
- Series identifiers verified against the live APIs; StatCan vector IDs set (CPI Ontario 41691919, unemployment rate Ontario 2063949). First real ingest results in the M1 note.

### Changed

- QA scripts are Windows-first: rules and troubleshooting in `docs/qa/README.md`; every script has a one-time setup (uv install, PATH for the current window, clone) and starts with `cd $HOME\canada-data-migration`; M0 and M3 snippets moved from bash to PowerShell.
- Test fixtures are now trimmed responses recorded from the live APIs, not hand-written.

### Fixed

- `cdm` finds the repository root from any subfolder (for example `dbt\`), instead of failing with `FileNotFoundError` on `config\series.yml`.
- `cdm find-vector` pads the coordinate to the 10 positions WDS requires (a shorter one returned HTTP 406).

- Project plan for Phase 0 and Phase 1: repository structure, ADRs 0001-0009, milestone plan with QA scripts, progress tracker and milestone note for M0.
- MIT license, `.gitignore`, `.env.example` with empty keys, `MEMORY.md`.
- README with "work in progress" status, planned architecture diagram and data attribution.
