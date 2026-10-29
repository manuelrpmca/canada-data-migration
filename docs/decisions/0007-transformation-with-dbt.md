# 0007. Transformation with dbt Core

- Status: Accepted
- Date: 2026-10-29
- Milestone: M2

## Context

Raw observations need to become clean, tested, documented tables that a dashboard can use. dbt is the transformation tool most often named in data engineering job postings, and it is a gap in the owner's public evidence. The same models must run on DuckDB (v0.1) and BigQuery (v1.0).

## Options considered

1. **Plain SQL scripts run from Python.** No new tool, but no dependency graph, no built-in tests, no docs, no lineage.
2. **dbt Core** with the `dbt-duckdb` and `dbt-bigquery` adapters. Open source, runs in CI, built-in tests, source freshness and documentation.
3. **dbt Cloud.** Hosted IDE and scheduler, but needs an account and would split the pipeline between two platforms.
4. **SQLMesh.** Strong ideas (virtual environments, column-level lineage), but less recognized by recruiters today.

## Decision

dbt Core, in `dbt/`, with two targets: `duckdb` (default; local and CI) and `bigquery` (M5).

Modelling rules:

- **Sources** declare the raw tables with `freshness` checks (warn and error thresholds per frequency).
- **Staging** (`stg_`): one model per source table; rename, cast, deduplicate. No joins.
- **Marts**: a small star schema.
  - `dim_date`: calendar with business-day flag.
  - `dim_indicator`: one row per series (source, name, unit, frequency, attribution).
  - `fct_observation`: one row per indicator per reference date.
  - `mart_monthly_indicators`: one row per month with CPI, unemployment rate, average USD/CAD and the policy rate in effect, ready for the dashboard.
- **Tests** on every model: `not_null` and `unique` on keys, `relationships` from facts to dimensions, `accepted_values` where a column has a closed set, plus singular tests for business rules (for example, a policy rate within a plausible range).
- `dbt build` (run + test) is the single command in CI.

## Consequences

- The owner should complete the free dbt Fundamentals course before M2 so every model can be explained.
- Tests become documentation: a reader sees what the data guarantees.
- Adapter differences are isolated in macros; if a model cannot be made portable, the reason is written next to it.
