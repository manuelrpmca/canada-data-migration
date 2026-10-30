# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- M1 ingestion: `cdm` CLI (`ingest`, `status`, `verify`, `find-vector`), Bank of Canada Valet and Statistics Canada WDS clients with retries and back-off, raw landing, idempotent DuckDB upsert with lookback window, run log, unit tests, Dependabot config.
- QA script for M1 rewritten for PowerShell on Windows 11.
- Series identifiers verified against the live APIs; StatCan vector IDs set (CPI Ontario 41691919, unemployment rate Ontario 2063949). First real ingest results in the M1 note.

### Changed

- Test fixtures are now trimmed responses recorded from the live APIs, not hand-written.

### Fixed

- `cdm find-vector` pads the coordinate to the 10 positions WDS requires (a shorter one returned HTTP 406).

- Project plan for Phase 0 and Phase 1: repository structure, ADRs 0001-0009, milestone plan with QA scripts, progress tracker and milestone note for M0.
- MIT license, `.gitignore`, `.env.example` with empty keys, `MEMORY.md`.
- README with "work in progress" status, planned architecture diagram and data attribution.
