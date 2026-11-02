# M3. Automation and v0.1

Date closed: open · Owner hours: to be logged

## What was done

- `ci.yml`: lint, format, tests (including `dbt build` on a synthetic warehouse) and a CLI smoke test on every pull request, on Linux and Windows, in PowerShell ([ADR 0008](../decisions/0008-orchestration-and-ci.md)).
- `daily.yml`: the full pipeline against the live APIs every day at 15:00 UTC and on demand, with source freshness, a summary table and the warehouse as an artifact. The pull request that changes the workflow also runs it, plus a clean-checkout run on Windows.
- Clearer errors for the failures seen in the M2 QA run: HTTP 403 names the VPN, a connection error names the network, a missing warehouse names the command that creates it.
- README for v0.1, CHANGELOG entries, QA script.

## Why it was done this way

- **Windows in CI, in PowerShell.** The owner's QA runs on Windows 11 and M2's QA found seven environment problems that Linux-only checks could not. The Windows job uses the same shell and commands as the QA scripts. The new CLI smoke test paid off on its first run: it found that `cdm dbt --version` was rejected by the argument parser.
- **CI never calls the data APIs.** Unit tests use recorded fixtures and the dbt build runs on generated data, so a red CI means the code changed, not that an API was slow. The live APIs are exercised by the daily run, where a failure means the data or the network.
- **The daily run is incremental through the Actions cache.** A fresh runner would otherwise download the full history every day, which hides the lookback logic the project is meant to show. If the cache is gone the run falls back to a full backfill, so the cache is a speed-up, never a dependency. The key has a version (`warehouse-v1-`) to force a clean rebuild when the raw schema changes.
- **The workflow is tested before it reaches `main`.** `workflow_dispatch` only works once a workflow is on the default branch, so `daily.yml` also runs on pull requests that change it. That is how the first live run on GitHub's network (Azure, United States) was checked before review.
- **Supply chain basics.** Actions are pinned to commit SHAs (Dependabot updates them weekly), permissions are read-only, checkout does not keep the token, and the install uses the lock file (`uv sync --locked`).

## Measured results

Claude's environment (Linux), 2026-11-02 around 15:23 UTC, fresh clone of the M3 branch:

| Command | Result |
| --- | --- |
| `uv run cdm run` (empty warehouse) | 4 series `success`: usd_cad 2452 rows, policy_rate 2551, cpi_ontario 117, unemployment_ontario 117; PASS=66 WARN=0 ERROR=0; 21 seconds (dependencies already cached) |
| `uv run cdm ingest` again | 30 rows received in the lookback window, 0 inserted, 0 updated, 30 unchanged |
| `uv run cdm dbt source freshness` | 4 of 4 PASS |
| `uv run cdm --db nowhere.duckdb status` | Missing-warehouse message; no file created |
| `uv run pytest` | 56 passed |

GitHub Actions on the pull request (PR #10):

| Job | Result |
| --- | --- |
| `test (ubuntu-latest)`, `test (windows-latest)` | Green; the first Linux run failed on the CLI smoke test (`cdm dbt --version` rejected), fixed in the same PR |
| `daily / run` (live APIs, ubuntu) | First run green in 26 seconds; StatCan reachable from GitHub's runners |
| `daily / windows-fresh-run` (clean checkout, empty warehouse) | Green: 4 series `success`, PASS=66, freshness 4 of 4 PASS, 0.3 minutes with dependencies in the uv cache |

Owner's QA run on Windows 11: pending.

## What I would say in an interview

"Every pull request is tested on Linux and on Windows, because that's where I run it, and CI never touches the live APIs, so it's deterministic. A separate daily job runs the real pipeline incrementally, keeps its warehouse between runs, checks freshness per series, and leaves the database as a downloadable artifact. The first CI run caught a bug I would otherwise have found by hand."

## What I learned / what surprised me

- To be filled in by Manuel at milestone close.
