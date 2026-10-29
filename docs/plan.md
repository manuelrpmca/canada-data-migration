# Milestone plan

Plan for Phase 0 (foundations) and Phase 1 (release v0.1), with a sketch of Phase 2 (release v1.0). Dates assume **16-20 hours per week** from the owner. Hour figures are **planning estimates**, not measurements; actual hours are logged in the [tracker](progress/tracker.md) and the plan is re-dated if they drift.

## How every milestone works

1. Work happens on a feature branch, in one to three small pull requests. Nothing is pushed to `main` directly.
2. The owner reviews and merges. **A merge is the approval.**
3. The owner runs the milestone's QA script on their own machine (scripts in [qa/](qa/)).
4. The milestone closes with a short note in [notes/](notes/): what was done, why, and what to say about it in an interview.
5. The [tracker](progress/tracker.md), [CHANGELOG](../CHANGELOG.md) and [MEMORY.md](../MEMORY.md) are updated in the same pull request.

## Timeline

| Milestone | Window (2026) | Owner hours (estimate) | Exit criteria | QA script |
| --- | --- | --- | --- | --- |
| **M0. Foundations** (Phase 0) | Oct 29 - Nov 4 | 10-14, of which ~5-8 for the dbt Fundamentals course | Plan merged; repository security settings on; public profiles linked and consistent | [m0-foundations.md](qa/m0-foundations.md) |
| **M1. Ingestion** | Nov 2 - Nov 8 | 6-8 | `uv run cdm ingest` loads the four series into DuckDB; a second run changes nothing; unit tests pass offline | [m1-ingestion.md](qa/m1-ingestion.md) |
| **M2. dbt models** | Nov 9 - Nov 13 | 6-8 | `dbt build` passes on DuckDB: staging, star schema, tests, freshness | [m2-dbt-models.md](qa/m2-dbt-models.md) |
| **M3. Automation and v0.1** | Nov 12 - Nov 20 | 5-7 | CI green on every PR; daily run green; README final with diagram and one-command run; tag `v0.1` with release notes | [m3-automation-v0.1.md](qa/m3-automation-v0.1.md) |

**v0.1 target: Wednesday 2026-11-18, latest Friday 2026-11-20.** That is about three weeks from today, including Phase 0. Phase 1 alone (M1-M3) is about 17-23 owner hours, roughly one and a half weeks at the stated pace; the extra time is Phase 0 and buffer. It can move earlier if Phase 0 tasks run in parallel with M1.

## Phase 0. M0 Foundations

Inside this repository:

- [ ] Merge this plan (structure, ADRs 0001-0009, milestones, QA scripts, tracker, MEMORY, CHANGELOG, LICENSE, `.gitignore`, `.env.example`).
- [ ] Turn on repository settings: secret scanning and push protection, Dependabot alerts, and a branch rule on `main` that requires a pull request.

Outside this repository (from the project brief; owner tasks, tracked here so nothing is lost):

- [ ] GitHub profile README (a public repo named `manuelrpmca`), 10-15 lines, same headline as the website. Prepared as a pull request for the owner to review.
- [ ] Public Microsoft Learn transcript showing Azure Data Engineer Associate (2022-2026).
- [ ] Credly account.
- [ ] Tableau Public profile.
- [ ] dbt Fundamentals course and badge (before M2).
- [ ] LinkedIn Featured section linking the website.

Done when: the four public profiles (GitHub, LinkedIn, website, Credly) link to each other and show the same headline.

## Phase 1. Release v0.1

### M1. Ingestion

- Confirm series identifiers against the live APIs; write `config/series.yml` ([ADR 0003](decisions/0003-data-sources.md)).
- `pyproject.toml`, `uv.lock`, ruff, pytest, Dependabot config ([ADR 0004](decisions/0004-python-toolchain.md)).
- Valet and WDS clients with timeouts, back-off and HTTP 409 handling.
- Raw landing, DuckDB upsert, lookback window and run log ([ADR 0005](decisions/0005-ingestion-pattern.md)).
- Unit tests on recorded fixtures: parsing, upsert idempotency, watermark logic, retry helper.

### M2. dbt models

- dbt project with DuckDB target; sources with freshness.
- Staging models; `dim_date`, `dim_indicator`, `fct_observation`, `mart_monthly_indicators` ([ADR 0007](decisions/0007-transformation-with-dbt.md)).
- Generic and singular tests; dbt docs generate locally.
- `uv run cdm run` = ingest + `dbt build`.

### M3. Automation and v0.1

- `ci.yml` and `daily.yml` ([ADR 0008](decisions/0008-orchestration-and-ci.md)); CI badge in README.
- README final for v0.1: problem in one line, diagram, stack, one-command run, results from a real run, decisions, limits, next steps. "Work in progress" banner comes off.
- Tag `v0.1` and publish release notes (needs the owner's approval, as with anything public).

## Phase 2 sketch. Release v1.0

Planned at the start of Phase 2, after v0.1 is merged and tagged. Indicative only:

| Milestone | Window | Content |
| --- | --- | --- |
| M4. Legacy source | Nov 23 - Nov 29 | Oracle Free in Docker, bank-style schema, PL/SQL load package ([ADR 0009](decisions/0009-legacy-source-and-reconciliation.md)) |
| M5. Cloud migration | Nov 30 - Dec 6 | Oracle to BigQuery sandbox and DuckDB; dbt `bigquery` target |
| M6. Reconciliation | Dec 7 - Dec 13 | Counts, control totals, fingerprints, schema drift; HTML report on GitHub Pages |
| M7. Presentation and v1.0 | Dec 14 - Dec 20 | Tableau Public dashboard; case study on the owner's website by PR to that repository; tag `v1.0` |

## Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| A series identifier in ADR 0003 is wrong | M1 slips by hours | First task of M1 is to confirm identifiers live |
| StatCan locks tables before 8:30 a.m. Eastern (HTTP 409) | Failed scheduled run | Schedule after release time; treat 409 as retry-later |
| Owner hours fall below 16 per week | Dates slip | Re-date the plan in the tracker; scope stays fixed, dates move |
| Oracle Free is too heavy for CI runners | Oracle path not in CI | Measure in M4; fall back to a manual workflow ([ADR 0009](decisions/0009-legacy-source-and-reconciliation.md)) |
| BigQuery sandbox has no DML and 60-day expiry | Incremental loads impossible there | Replace-style loads, fully rebuildable tables ([ADR 0006](decisions/0006-warehouses.md)) |
