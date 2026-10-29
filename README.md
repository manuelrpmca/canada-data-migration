# Canada Data Migration

> **Work in progress.** Nothing here runs yet. This repository currently holds the plan: scope, architecture decisions and milestones. The first runnable release is v0.1 (see [the milestone plan](docs/plan.md)).

A small, public version of a real-world data migration: ingest Canadian open data, load it into a "legacy" database, migrate it to a cloud warehouse, and **prove that the data arrived intact** with automated reconciliation.

## What it will do

| Step | v0.1 (local, no cloud) | v1.0 (adds legacy source and cloud) |
| --- | --- | --- |
| Ingest | Python pulls Bank of Canada (Valet API) and Statistics Canada (WDS) series, incrementally and idempotently | Same |
| Legacy source | Not yet | Oracle Database Free in Docker, bank-style schema, PL/SQL load package |
| Warehouse | DuckDB | BigQuery (sandbox) and DuckDB |
| Transform | dbt: staging and marts, star schema, tests, source freshness | Same, on both targets |
| Reconcile | Not yet | Row counts, control totals and per-partition fingerprints, Oracle vs. targets; HTML report on GitHub Pages |
| Orchestrate | GitHub Actions: CI on every PR, daily scheduled run | Same |
| Present | README with diagram, one-command run | Tableau Public dashboard |

## Planned architecture

```mermaid
flowchart LR
    subgraph Sources["Open data APIs"]
        BOC["Bank of Canada<br/>Valet API"]
        STC["Statistics Canada<br/>WDS"]
    end
    BOC --> ING["Python ingestion<br/>(incremental, idempotent)"]
    STC --> ING
    ING --> RAW[("Raw landing<br/>JSON files")]
    RAW --> DDB[("DuckDB")]
    RAW -. v1.0 .-> ORA[("Oracle Free<br/>legacy source")]
    ORA -. v1.0 migration .-> BQ[("BigQuery")]
    ORA -. v1.0 migration .-> DDB
    DDB --> DBT["dbt<br/>staging → marts"]
    BQ -.-> DBT
    ORA -. v1.0 .-> REC["Reconciliation<br/>report"]
    BQ -.-> REC
    DDB -.-> REC
```

Solid lines are v0.1; dotted lines arrive in v1.0.

## Documentation

- [Milestone plan](docs/plan.md) and [progress tracker](docs/progress/tracker.md)
- [Architecture decision records](docs/decisions/README.md)
- [Repository structure](docs/structure.md)
- [QA scripts](docs/qa/) and [milestone notes](docs/notes/)
- [Changelog](CHANGELOG.md)

## Data attribution

- Adapted from Statistics Canada data tables (the exact tables and reference dates are listed in [ADR 0003](docs/decisions/0003-data-sources.md) and will appear with each run's output), used under the [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence). This does not constitute an endorsement by Statistics Canada of this product.
- Exchange rate and interest rate data from the [Bank of Canada](https://www.bankofcanada.ca/), via the [Valet API](https://www.bankofcanada.ca/valet-api-how-to/), subject to the Bank's [terms of use](https://www.bankofcanada.ca/terms/).

This project is not affiliated with or endorsed by Statistics Canada or the Bank of Canada.

## License

Code is released under the [MIT License](LICENSE). Data belongs to its publishers and keeps their terms.
