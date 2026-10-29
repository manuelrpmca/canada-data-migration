# Architecture decision records

Each significant decision gets a short record: the context, the options considered, the choice and its consequences. The format is a trimmed version of [MADR](https://adr.github.io/madr/).

Rules (see [ADR 0001](0001-record-architecture-decisions.md)):

- An ADR is **accepted when the pull request that adds it is merged** by the repository owner.
- Accepted ADRs are not rewritten. A changed decision gets a new ADR that supersedes the old one, and the old one's status is updated to point to it.
- A decision marked **Proposed** is a direction, not a commitment; it is confirmed or replaced when its milestone starts.

| # | Decision | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-scope-and-non-goals.md) | Scope, phases and non-goals | Accepted |
| [0003](0003-data-sources.md) | Data sources and initial series | Accepted |
| [0004](0004-python-toolchain.md) | Python toolchain | Accepted |
| [0005](0005-ingestion-pattern.md) | Ingestion pattern: raw landing, upsert, lookback window | Accepted |
| [0006](0006-warehouses.md) | Warehouses: DuckDB now, BigQuery sandbox later | Accepted |
| [0007](0007-transformation-with-dbt.md) | Transformation with dbt Core | Accepted |
| [0008](0008-orchestration-and-ci.md) | Orchestration and CI with GitHub Actions | Accepted |
| [0009](0009-legacy-source-and-reconciliation.md) | Legacy source (Oracle Free) and reconciliation approach | Proposed |

New ADRs copy [template.md](template.md).
