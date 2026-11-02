# Progress tracker

Live status of every milestone task. Updated in each pull request.

Last updated: 2026-11-02

## Milestones

| Milestone | Status | Window | Est. hours | QA run | Note |
| --- | --- | --- | --- | --- | --- |
| M0. Foundations | In progress (plan merged) | Oct 29 - Nov 4 | 10-14 | | [m0](../notes/m0-foundations.md) |
| M1. Ingestion | In progress | Nov 2 - Nov 8 | 6-8 | | [m1](../notes/m1-ingestion.md) |
| M2. dbt models | Merged; QA passed on Windows 11 | Nov 9 - Nov 13 | 6-8 | 2026-11-02 | [m2](../notes/m2-dbt-models.md) |
| M3. Automation and v0.1 | QA passed on Windows 11; release PR open | Nov 12 - Nov 20 | 5-7 | 2026-11-02 | [m3](../notes/m3-automation-v0.1.md) |

## M0 tasks

| Task | Owner | Status | Link |
| --- | --- | --- | --- |
| Plan: structure, ADRs 0001-0009, milestones, QA scripts | Claude | Done | PR #1 |
| Repo settings: secret scanning, push protection, Dependabot alerts, `main` requires PR | Manuel | Not started | [QA M0](../qa/m0-foundations.md) |
| GitHub profile README (`manuelrpmca/manuelrpmca`) | Claude drafts, Manuel approves | Not started | |
| Microsoft Learn public transcript | Manuel | Not started | |
| Credly account | Manuel | Not started | |
| Tableau Public profile | Manuel | Not started | |
| dbt Fundamentals course and badge | Manuel | Not started | |
| LinkedIn Featured links the website | Manuel | Not started | |

## M1 tasks

| Task | Owner | Status | Link |
| --- | --- | --- | --- |
| Python project: pyproject, uv.lock, ruff, pytest, Dependabot | Claude | Done | PR #2 |
| Valet and WDS clients with timeouts, back-off, HTTP 409 handling | Claude | Done | PR #2 |
| Raw landing, DuckDB upsert, lookback window, run log | Claude | Done | PR #2 |
| CLI: `cdm ingest`, `status`, `verify`, `find-vector` | Claude | Done | PR #2 |
| Unit tests on fixtures, no network | Claude | Done | PR #2 |
| Confirm series identifiers against the live APIs; set StatCan vector IDs | Claude | Done | PR #3 |
| Replace hand-written fixtures with recorded responses | Claude | Done | PR #3 |
| First real ingest (two runs, idempotent) and results in the M1 note | Claude | Done | PR #3 |
| Run the M1 QA script on Windows 11 | Manuel | Not started | [QA M1](../qa/m1-ingestion.md) |

## M2 tasks

| Task | Owner | Status | Link |
| --- | --- | --- | --- |
| dbt project, DuckDB target, sources with per-series freshness | Claude | Done | PR #4 |
| Staging models; `dim_date`, `dim_indicator`, `fct_observation`, `mart_monthly_indicators` | Claude | Done | PR #4 |
| Generic and singular tests, unit test for the mart; `dbt docs generate` | Claude | Done | PR #4 |
| `uv run cdm run` = ingest + `dbt build`; `cdm sql` for QA | Claude | Done | PR #4 |
| Offline pytest that builds the dbt project on synthetic data | Claude | Done | PR #4 |
| dbt Fundamentals course (before reviewing M2) | Manuel | Not started | |
| Run the M2 QA script on Windows 11 | Manuel | Done 2026-11-02 (break-a-test steps 7-9 optional, not run) | [QA M2](../qa/m2-dbt-models.md) |
| Windows fixes found in QA: `cdm dbt`, root search from subfolders, troubleshooting table | Claude | Done | PRs #5, #6, #7 |

## M3 tasks

| Task | Owner | Status | Link |
| --- | --- | --- | --- |
| `ci.yml`: lint, format, tests, dbt build, CLI smoke test on Linux and Windows | Claude | Done | PR #10 |
| `daily.yml`: live run, freshness, summary, artifact, incremental through the cache | Claude | Done | PR #10 |
| Clear errors: HTTP 403 (VPN), connection error, missing warehouse | Claude | Done | PR #10 |
| README v0.1 with badges and real-run results; CHANGELOG; M3 QA script and note | Claude | Done | PR #10 |
| Fresh-clone dry run of the QA script before handoff | Claude | Done (Linux; Windows covered by CI jobs) | PR #10 |
| Run the M3 QA script on Windows 11 | Manuel | Done 2026-11-02 | [QA M3](../qa/m3-automation-v0.1.md) |
| README chart from real data (`cdm chart`) and dbt docs on GitHub Pages, refreshed daily | Claude | Done | Release PR |
| Regulated-sector framing for v1.0 in README, ADR 0002, ADR 0009, plan, structure | Claude | Done | Release PR |
| Turn on GitHub Pages: Settings > Pages > Source: GitHub Actions | Manuel | Not started | |
| Release PR: CHANGELOG 0.1.0, version, QA results, release notes | Claude | Done | Release PR |
| Publish release `v0.1` | Manuel | After the release PR | |

## Open questions

| Question | Asked | Answer |
| --- | --- | --- |
| Which OS does Manuel run the QA scripts on (macOS, Windows, Linux)? | 2026-10-29 | Windows 11; QA scripts use PowerShell |
| Are the v0.1 series (USD/CAD, policy rate, Ontario CPI, Ontario unemployment rate) the right four? | 2026-10-29 | Yes |

## Log

| Date | Event |
| --- | --- |
| 2026-11-02 | Owner's M2 QA on Windows 11: `cdm run` PASS=66 ERROR=0, freshness 4 of 4 PASS, docs generated and served. PRs #6 and #7 merged. |
| 2026-11-02 | QA scripts made Windows-first after the owner's first Windows run (repo not cloned, uv not on PATH). PR #4 (M2) and PR #5 merged. |
| 2026-11-01 | M2 dbt models built; `dbt build` PASS=66 on real data. PR opened. |
| 2026-10-30 | PR #3 merged: live ID verification and first real ingest. |
| 2026-10-30 | Series identifiers verified live; StatCan vectors 41691919 and 2063949 set; first real ingest recorded in the M1 note. |
| 2026-10-30 | PR #2 merged: M1 ingestion code. |
| 2026-10-29 | M1 started on branch `feat/m1-ingestion`. |
| 2026-10-29 | PR #1 merged: plan, ADRs 0001-0008 accepted. |
| 2026-10-29 | Repository created (public, empty README). Plan proposed in PR #1. |
