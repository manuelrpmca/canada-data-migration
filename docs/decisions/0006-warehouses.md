# 0006. Warehouses: DuckDB now, BigQuery sandbox later

- Status: Accepted
- Date: 2026-10-29
- Milestone: M1 (DuckDB), M5 (BigQuery)

## Context

The project's target is a cloud warehouse, and the job market asks for visible GCP and BigQuery experience. But v0.1 must run on any laptop and in CI with no credentials and no cost ([ADR 0002](0002-scope-and-non-goals.md)). The owner's employment contract allows public projects with GCP and BigQuery (confirmed by the owner on 2026-10-29).

Facts checked on 2026-10-29 in the [BigQuery sandbox documentation](https://docs.cloud.google.com/bigquery/docs/sandbox): no credit card; 10 GiB of storage (a lifetime allowance; deleting data does not give it back); 1 TiB of query processing per month; tables, views and partitions expire after 60 days; **no DML statements** (no `INSERT`, `UPDATE`, `MERGE`), no streaming, no Data Transfer Service.

## Options considered

1. **BigQuery only.** Most realistic target, but CI and every local run would need cloud credentials, and the sandbox limits (no DML, 60-day expiry) shape the design.
2. **DuckDB only.** Free, embedded, fast, perfect for CI, but does not show cloud skills.
3. **DuckDB for local and CI, BigQuery sandbox as the cloud target in v1.0.** Same dbt models, two targets.
4. **Snowflake or Databricks free tiers.** Possible, but trials expire or need accounts, and the owner's current work is on GCP.

## Decision

Option 3.

- **DuckDB** is the v0.1 warehouse: a single file at `data/warehouse.duckdb`, created by the pipeline. Upserts use DuckDB's `INSERT ... ON CONFLICT` or `MERGE`.
- **BigQuery sandbox** joins in M5 as the cloud target of the migration. Because the sandbox has no DML, loads to BigQuery use **load jobs that replace a table or partition** (`WRITE_TRUNCATE`), and dbt models on BigQuery are materialized as tables or views, not incremental merges. The 60-day expiry is handled by making every BigQuery table fully rebuildable from the source in one run.
- Moving out of the sandbox (enabling billing) is out of scope unless the owner approves it.

## Consequences

- v0.1 needs no cloud account; anyone can clone and run it.
- Writing the same models for two engines forces portable SQL; engine-specific SQL goes into dbt macros with a branch per adapter.
- The BigQuery load strategy differs from the DuckDB one (replace vs. merge). This is documented as a deliberate consequence of the sandbox, and it is a useful talking point: the reconciliation in v1.0 proves both paths give the same result.
