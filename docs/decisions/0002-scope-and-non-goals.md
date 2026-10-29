# 0002. Scope, phases and non-goals

- Status: Accepted
- Date: 2026-10-29
- Milestone: M0

## Context

The project reproduces, at small scale and with open data only, the kind of work done in enterprise data migrations: moving data from a legacy relational database to a cloud warehouse and proving that it arrived intact. The owner has 16-20 hours per week and wants a finished, verifiable result quickly. A small finished project is worth more than a large unfinished one.

## Options considered

1. **Build everything at once** (ingestion, Oracle, BigQuery, dbt, reconciliation, dashboard) and release at the end. Risky: nothing is shown until everything works.
2. **Two releases.** v0.1 is a complete, local, cloud-free pipeline; v1.0 adds the legacy source, the cloud warehouse and reconciliation.
3. **Start with the migration** (Oracle to BigQuery) and add ingestion later. Puts the hardest, least portable parts first and makes CI depend on cloud credentials from day one.

## Decision

Option 2.

**v0.1 (Phase 1): local pipeline.** Ingest a small set of Bank of Canada and Statistics Canada series ([ADR 0003](0003-data-sources.md)) incrementally and idempotently, load them into DuckDB, model them with dbt (staging, marts, tests, freshness), run CI on every pull request and a daily scheduled run, and document it in a README with a diagram and a one-command run.

**v1.0 (Phase 2): migration and proof.** Add Oracle Database Free as the "legacy" source with a bank-style schema and a PL/SQL load package, migrate to BigQuery (sandbox) and DuckDB, reconcile source and targets (row counts, control totals, per-partition fingerprints, schema drift) with an HTML report on GitHub Pages, and publish a Tableau Public dashboard.

**Non-goals** (explicitly out of scope for v1.0):

- A general-purpose orchestrator (Airflow, Kestra, Dagster). GitHub Actions is enough at this scale ([ADR 0008](0008-orchestration-and-ci.md)); an orchestrator may come in a later phase.
- Infrastructure as code (Terraform). The sandbox needs almost no infrastructure.
- Streaming, Spark, Kafka or any "big data" tooling. The data is small; using them would be decoration.
- Paid cloud services. Any spending needs the owner's explicit approval.
- A reusable, published reconciliation library. Reconciliation lives inside this project and is only extracted if it becomes clean and someone asks for it.
- Any data, code, table names or screenshots from current or past employers or clients. Open data only.

## Consequences

- v0.1 runs on any laptop and in CI with no credentials, which keeps the first release fast and easy to verify.
- The migration story (the most distinctive part) only appears in v1.0; until then the README says "work in progress".
- Every published number must come from a real run of this project.
