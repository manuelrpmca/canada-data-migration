# 0009. Legacy source (Oracle Free) and reconciliation approach

- Status: Accepted (legacy source, M4, 2026-11-02). The migration and reconciliation parts stay as proposed until M5 and M6.
- Date: 2026-10-29, accepted 2026-11-02
- Milestone: M4-M6

## Context

v1.0 tells the migration story: a "legacy" relational database is the system of record, data moves to a cloud warehouse, and an automated reconciliation proves it arrived intact. This mirrors common enterprise migrations, using open data only. Datafold stopped maintaining its open-source `data-diff` tool on 2024-05-17 ([Datafold docs](https://docs.datafold.com/reference/open_source/)), so a small, readable reconciliation implementation has value of its own.

## Options considered

Legacy source:

1. **Oracle Database Free in Docker.** Free, runs locally, PL/SQL available; Oracle is a common legacy platform in banking, insurance and the public sector.
2. **PostgreSQL.** Lighter and easier in CI, but a weaker "legacy enterprise" story and no PL/SQL.

Container image (settled in M4):

1. **`container-registry.oracle.com/database/free`**, Oracle's own image. Creates the database on first start, which takes several minutes.
2. **`gvenzl/oracle-free`**, the community image maintained by Gerald Venzl (Oracle product manager), Apache-2.0, on Docker Hub. Its `slim-faststart` variant ships with the database already created.

Reconciliation:

1. **Write it in Python** with checks expressed as SQL run on each engine: row counts, control totals (sums of values), per-partition fingerprints (hash of sorted rows per month and series), and schema comparison.
2. **Use a library** (for example the community fork of data-diff, or Great Expectations for checks). Less code, but more dependencies and less of the owner's own reasoning on display.

## Decision

### Legacy source (built in M4)

- **Oracle Database Free 23.26.3** (Oracle AI Database 26ai Free) from `gvenzl/oracle-free:23.26.3-slim-faststart`, pinned by digest in `docker-compose.yml`, port bound to `127.0.0.1` only, data in a named volume. Measured on 2026-11-02 in Claude's Linux environment: ready 39 seconds after `docker run`, about 20 seconds on later starts; 2.1 GiB of memory once open; 1.3 GB download, 6.5 GB on disk. Started with `uv run cdm oracle up`, which also creates random passwords in the git-ignored `.env` and runs setup, so the owner never types Docker or SQL*Plus commands.
- **Governed schema**, modelled the way regulated organizations (banks, insurers, public sector) keep data, in `oracle/ddl/`:
  - `SOURCE_SYSTEM` and `SERIES` reference tables.
  - `LANDED_FILE`: every API response kept unchanged (JSON, `IS JSON` check) with its SHA-256, fetch time and loading user, so any load can be replayed and audited.
  - `OBSERVATION_REVISION`: **effective-dated revisions**. Each value has `known_from` (when it was first received) and `known_to` (when a revised value replaced it). A unique index on open rows guarantees one current value per period. Views: `OBSERVATION_CURRENT`, and `OBSERVATION_AS_OF(timestamp)`, a SQL macro that answers "what was known on day X".
  - `LOAD_AUDIT`: one row per load attempt, including failed ones (written in an autonomous transaction, so it survives the rollback).
  - **Data dictionary and classification**: every table and column has a `COMMENT` and a `classification` annotation (Oracle 23ai annotations), `Public` for the published data and its reference metadata, `Internal` for operational metadata. `DATA_DICTIONARY` is refreshed from Oracle's own catalog on every setup. A view over the catalog was the first choice, but Oracle does not let a schema re-grant its catalog views to a role (ORA-01720), so the dictionary is a table that setup rewrites. A test checks it matches the catalog and has no gaps.
- **Separate accounts** (`oracle/ddl/01_accounts.sql`): `CDM_OWNER` owns everything and is a schema-only account (`NO AUTHENTICATION`, reached for DDL only through a proxy connection from `SYSTEM`); `CDM_LOADER` can only execute the load package; `CDM_MIGRATION` (the account M5 will read with) can only select. Tests check both limits.
- **PL/SQL package `CDM_LOAD`** (`oracle/plsql/`): Python sends each landed file as received; the package parses it with `JSON_TABLE`, applying the same rules as the Python parsers, and applies it in one transaction per file. A changed value closes the current revision and opens a new one; a new period opens one; an unchanged value does nothing. A single `MERGE`, as in [ADR 0005](0005-ingestion-pattern.md), was set aside for observations because it would overwrite revised values in place and lose the history; `MERGE` is used for the reference tables. Files of a series must arrive in fetch order; an older file is refused and audited.
- Python connects with `python-oracledb` in thin mode (no Oracle client install).
- **CI**: an `oracle` job on `ubuntu-latest` starts the container with `uv run cdm oracle up`, the same command as the QA script, and runs the integration tests. GitHub's Windows runners cannot run Linux containers, so the Windows path is covered by the owner's QA. Measured on the first run (PR #12, 2026-11-02): image pulled in about 45 seconds, container healthy 6 seconds after start, 1.98 GiB of memory, whole job 78 seconds.
- Every published value is still the publisher's; the database is a governed copy, not a new source of truth for the figures.

### Migration and reconciliation (proposed, settled in M5 and M6)

- **Migration** reads from Oracle as `CDM_MIGRATION` and loads BigQuery (load jobs, [ADR 0006](0006-warehouses.md)) and DuckDB.
- **Reconciliation** written in Python, per source/target pair: counts, control totals, per-partition fingerprints and schema drift, with results stored in a table and rendered as a static HTML report on GitHub Pages on every run. M4 adds only a basic check, `cdm oracle compare` (rows, first and last period, sum of values per series, Oracle against DuckDB).

## Consequences

- Shows Oracle, PL/SQL, migration and reconciliation in one place, the core of the owner's experience.
- The governance features are inspired by practices common in regulated sectors; the project does not claim compliance with any specific regulation or standard (owner decision, 2026-11-02).
- The project holds no personal or confidential data, so the classification levels exist to show the mechanism, not to protect anything.
- Oracle needs Docker Desktop on Windows and about 2 GiB of free memory and 7 GB of disk. The README states this.
- Oracle and DuckDB can differ on one edge case by design: DuckDB loads only the periods inside each run's request window, Oracle every period in the file from the series start date. On the same files they matched on all four series (2026-11-02).
- `CREATE TABLE IF NOT EXISTS` keeps setup re-runnable but does not alter an existing table. While the schema is young, a table change means `uv run cdm oracle down --delete-data` and a reload from the landed files, which are the source of truth for replays.
