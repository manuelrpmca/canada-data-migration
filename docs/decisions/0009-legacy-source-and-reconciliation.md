# 0009. Legacy source (Oracle Free) and reconciliation approach

- Status: Proposed (confirmed or replaced at the start of M4)
- Date: 2026-10-29
- Milestone: M4-M6

## Context

v1.0 tells the migration story: a "legacy" relational database is the system of record, data moves to a cloud warehouse, and an automated reconciliation proves it arrived intact. This mirrors common enterprise migrations, using open data only. Datafold stopped maintaining its open-source `data-diff` tool on 2024-05-17 ([Datafold docs](https://docs.datafold.com/reference/open_source/)), so a small, readable reconciliation implementation has value of its own.

## Options considered

Legacy source:

1. **Oracle Database Free in Docker.** Free, runs locally, PL/SQL available; Oracle is a common legacy platform in banking and insurance.
2. **PostgreSQL.** Lighter and easier in CI, but a weaker "legacy enterprise" story and no PL/SQL.

Reconciliation:

1. **Write it in Python** with checks expressed as SQL run on each engine: row counts, control totals (sums of values), per-partition fingerprints (hash of sorted rows per month and series), and schema comparison.
2. **Use a library** (for example the community fork of data-diff, or Great Expectations for checks). Less code, but more dependencies and less of the owner's own reasoning on display.

## Proposed decision

- **Oracle Database Free** in Docker (`docker-compose.yml`), with a bank-style schema (reference tables, a fact table of observations, an audit/run table) and a **PL/SQL package** that loads landed files with `MERGE`, mirroring [ADR 0005](0005-ingestion-pattern.md). Python connects with `python-oracledb` in thin mode (no Oracle client install).
- **Migration** reads from Oracle and loads BigQuery (load jobs, [ADR 0006](0006-warehouses.md)) and DuckDB.
- **Reconciliation** written in Python, per source/target pair: counts, control totals, per-partition fingerprints and schema drift, with results stored in a table and rendered as a static HTML report on GitHub Pages on every run.
- In CI, Oracle runs as a service container only if it fits within the runner's time and memory; otherwise the Oracle path runs locally and in a manual workflow. To be measured in M4, not assumed.

Open points to settle at M4: the exact Oracle Free image and version, its resource limits, and CI start-up time.

## Consequences

- Shows Oracle, PL/SQL, migration and reconciliation in one place, the core of the owner's experience.
- Oracle in Docker is heavy; the README will state the machine requirements once measured.
