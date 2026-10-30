# MEMORY

Working memory for this repository: the rules that do not change, the conventions in use and where things stand. Read this first before working on the project. Keep it short; details belong in ADRs, the plan and the tracker.

## Purpose

Public portfolio project: ingest Canadian open data, load a "legacy" Oracle source, migrate to BigQuery and DuckDB, transform with dbt, and prove the data arrived intact with automated reconciliation. Message: "I move data to the cloud and prove it arrived intact."

## Rules

1. **No invented numbers or experience.** Every published figure comes from a real run of this project, with the date and command that produced it.
2. **Open data only.** No code, data, table names or screenshots from any current or past employer or client.
3. **Branches and pull requests only.** Never push to `main`. The owner's merge is the approval.
4. **Nothing public without approval.** Tags, releases, GitHub Pages, dashboards and posts need the owner's explicit OK.
5. **No spending without approval.** Free tiers only (BigQuery sandbox, GitHub Actions on a public repo, Tableau Public).
6. **Secrets** only in a git-ignored `.env` or GitHub Actions secrets. `.env.example` keeps empty keys.
7. **English** for everything in the repository: code, comments, commits, PRs, docs.
8. **Attribution** for Statistics Canada and the Bank of Canada on every published output (see README).
9. **Explainable.** Every milestone closes with a note and a QA run on the owner's machine.

## Conventions

- ADRs in `docs/decisions/`, numbered, accepted on merge, superseded rather than rewritten.
- One QA script per milestone in `docs/qa/`; one note per milestone in `docs/notes/`.
- Tracker in `docs/progress/tracker.md`, updated in every PR.
- CHANGELOG in Keep a Changelog format; versions `v0.1`, `v1.0`.
- Commit messages: imperative mood, short subject (for example, "Add Valet API client").
- Python 3.12, uv, ruff, pytest; single CLI `uv run cdm <command>` ([ADR 0004](docs/decisions/0004-python-toolchain.md)).

## Current state

- Phase 1. M0 plan merged (PR #1); owner's Phase 0 tasks in progress. M1 ingestion in progress.
- Owner time: 16-20 hours per week. Owner runs QA on Windows 11: QA scripts use PowerShell, no `make` or bash-only syntax.
- Series identifiers are not yet verified against the live APIs; StatCan vector IDs are empty until `cdm verify` / `cdm find-vector` confirm them.
- Test fixtures are hand-written and synthetic until replaced by recorded responses.

## Key facts checked (2026-10-29)

- BigQuery sandbox: no DML, no streaming, tables expire after 60 days, 10 GiB storage, 1 TiB queries per month ([ADR 0006](docs/decisions/0006-warehouses.md)).
- StatCan WDS: 25 requests per second per IP; data released 8:30 a.m. Eastern; HTTP 409 while tables are locked ([ADR 0003](docs/decisions/0003-data-sources.md)).
- Valet API: no key; back off on failure; cache daily data.
