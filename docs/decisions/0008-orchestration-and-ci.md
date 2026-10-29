# 0008. Orchestration and CI with GitHub Actions

- Status: Accepted
- Date: 2026-10-29
- Milestone: M3

## Context

The pipeline needs a daily schedule and checks on every pull request. The workload is a few API calls and a small dbt build. GitHub Actions is free for public repositories ([GitHub docs](https://docs.github.com/en/actions/concepts/billing-and-usage)).

## Options considered

1. **GitHub Actions** for both CI and the daily schedule. Zero infrastructure, visible run history, a green badge on the README.
2. **Airflow, Kestra or Dagster.** Recognized orchestrators, but each needs a server or a hosted account, and they add more to explain than they add value at this size.
3. **Local cron on the owner's machine.** Free, but invisible to reviewers and dependent on one laptop.

## Decision

GitHub Actions, with two workflows:

- **`ci.yml`, on every pull request and push to `main`:** `uv sync`, `ruff check`, `ruff format --check`, `pytest`, then `dbt build` against DuckDB using recorded fixtures (no network), so CI is deterministic.
- **`daily.yml`, scheduled once a day and runnable by hand (`workflow_dispatch`):** full run against the live APIs (ingest, then `dbt build` including source freshness). Scheduled after StatCan's 8:30 a.m. Eastern release ([ADR 0003](0003-data-sources.md)), around 15:00 UTC. The DuckDB file and run log are uploaded as workflow artifacts; in v1.0 the reconciliation report is published to GitHub Pages.

Workflows use pinned action versions, the minimum `permissions`, and no secrets in v0.1.

An orchestrator is a candidate for a later phase (for example as part of the DataTalksClub Zoomcamp), recorded in a new ADR if adopted.

## Consequences

- GitHub disables scheduled workflows in public repositories after 60 days without repository activity; regular commits avoid that, and the README states it.
- Scheduled runs can start late when GitHub is busy; nothing depends on exact timing.
- A failed daily run is visible in the Actions tab and emails the owner; that is the alerting for now.
