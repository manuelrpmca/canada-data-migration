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
10. **QA scripts are Windows-first.** The owner runs them in PowerShell on Windows 11. Follow the rules in [docs/qa/README.md](docs/qa/README.md): PowerShell syntax only, the one-time setup in every script, `cd $HOME\canada-data-migration` as the first and only `cd`, dbt via `uv run cdm dbt ...`, and every new error added to its troubleshooting table.

## Conventions

- ADRs in `docs/decisions/`, numbered, accepted on merge, superseded rather than rewritten.
- One QA script per milestone in `docs/qa/`; one note per milestone in `docs/notes/`.
- Tracker in `docs/progress/tracker.md`, updated in every PR.
- CHANGELOG in Keep a Changelog format; versions `v0.1`, `v1.0`.
- Commit messages: imperative mood, short subject (for example, "Add Valet API client").
- Python 3.12, uv, ruff, pytest; single CLI `uv run cdm <command>` ([ADR 0004](docs/decisions/0004-python-toolchain.md)).

## Working agreement (from the M2 retrospective, 2026-11-02)

**Definition of done for a milestone pull request.** Before asking the owner to review:

1. Lint, format and tests pass, and the change ran against real data. Say where: "verified in Claude's Linux environment" is not "verified on Windows".
2. The QA script was run top to bottom from a fresh clone in an empty folder, exactly as written. Any step that needs a tool, a folder or a network condition says so.
3. Every command in the QA script works from the repository folder (no `cd` into subfolders) and is listed in `cdm --help` or the uv docs.
4. Known environment risks are written in the QA script before the run (VPN, company network, first-time downloads), not discovered during it.
5. From M3 on, CI runs the tests on `windows-latest` as well as Linux, so Windows problems show up before the owner's QA.

**QA handoff protocol.**

- One handoff message per milestone: three to five commands with the expected result of each, copied from the merged QA script. No other commands in chat.
- No changes to the guide or code while the owner is running QA. Problems found during QA are answered in chat with a workaround, then fixed together in **one** follow-up pull request after the run.
- Every error the owner hits goes into the troubleshooting table in [docs/qa/README.md](docs/qa/README.md).
- Before answering an error, read it fully and name its cause (code, environment or instructions), then give one fix.

**Pull requests.** At most two per milestone (the work, then one follow-up). Small doc fixes wait for the next pull request instead of opening their own.

## Current state

- Phase 1. M0 plan merged (PR #1); owner's Phase 0 tasks in progress. M1 ingestion merged (PRs #2, #3), owner QA pending. M2 dbt models in review.
- Owner time: 16-20 hours per week. Owner runs QA on Windows 11: QA scripts use PowerShell, no `make` or bash-only syntax.
- Series identifiers verified against the live APIs on 2026-10-30 (see the [M1 note](docs/notes/m1-ingestion.md)). StatCan vectors: CPI Ontario 41691919, unemployment rate Ontario 2063949.
- Test fixtures are trimmed responses recorded on 2026-10-30; edge cases (empty or null values) use inline synthetic payloads in the tests.
- WDS coordinates need all 10 positions; `cdm find-vector` pads them.
- dbt project in `dbt/`; run with `uv run cdm run` or `uv run cdm dbt <command>` from any folder. Schemas in the DuckDB file: `raw` (ingest), `staging`, `marts`, `reference` (seeds).
- Business days are inferred from USD/CAD publication days (the policy rate has values on holidays). Adapter-specific SQL goes in macros (`date_spine`).

## Key facts checked (2026-10-29)

- BigQuery sandbox: no DML, no streaming, tables expire after 60 days, 10 GiB storage, 1 TiB queries per month ([ADR 0006](docs/decisions/0006-warehouses.md)).
- StatCan WDS: 25 requests per second per IP; data released 8:30 a.m. Eastern; HTTP 409 while tables are locked ([ADR 0003](docs/decisions/0003-data-sources.md)).
- Valet API: no key; back off on failure; cache daily data.
