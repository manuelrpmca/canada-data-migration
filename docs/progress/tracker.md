# Progress tracker

Live status of every milestone task. Updated in each pull request. Hours are the owner's actual hours, logged at milestone close; estimates live in the [plan](../plan.md).

Last updated: 2026-10-30

## Milestones

| Milestone | Status | Window | Est. hours | Actual hours | QA run | Note |
| --- | --- | --- | --- | --- | --- | --- |
| M0. Foundations | In progress (plan merged) | Oct 29 - Nov 4 | 10-14 | | | [m0](../notes/m0-foundations.md) |
| M1. Ingestion | In progress | Nov 2 - Nov 8 | 6-8 | | | [m1](../notes/m1-ingestion.md) |
| M2. dbt models | Not started | Nov 9 - Nov 13 | 6-8 | | | |
| M3. Automation and v0.1 | Not started | Nov 12 - Nov 20 | 5-7 | | | |

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

## Open questions

| Question | Asked | Answer |
| --- | --- | --- |
| Which OS does Manuel run the QA scripts on (macOS, Windows, Linux)? | 2026-10-29 | Windows 11; QA scripts use PowerShell |
| Are the v0.1 series (USD/CAD, policy rate, Ontario CPI, Ontario unemployment rate) the right four? | 2026-10-29 | Yes |

## Log

| Date | Event |
| --- | --- |
| 2026-10-30 | Series identifiers verified live; StatCan vectors 41691919 and 2063949 set; first real ingest recorded in the M1 note. |
| 2026-10-30 | PR #2 merged: M1 ingestion code. |
| 2026-10-29 | M1 started on branch `feat/m1-ingestion`. |
| 2026-10-29 | PR #1 merged: plan, ADRs 0001-0008 accepted. |
| 2026-10-29 | Repository created (public, empty README). Plan proposed in PR #1. |
