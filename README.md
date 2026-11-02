# Canada Data Migration

[![ci](https://github.com/manuelrpmca/canada-data-migration/actions/workflows/ci.yml/badge.svg)](https://github.com/manuelrpmca/canada-data-migration/actions/workflows/ci.yml)
[![daily](https://github.com/manuelrpmca/canada-data-migration/actions/workflows/daily.yml/badge.svg)](https://github.com/manuelrpmca/canada-data-migration/actions/workflows/daily.yml)

**I move data to the cloud and prove it arrived intact.** This repository is a small, public version of a real-world data migration, built on Canadian open data.

> **Status: v0.1.** Four public economic series are ingested every day, modelled with dbt and tested on every change, on Linux and Windows. v1.0 adds a "legacy" Oracle source, a BigQuery target and automated reconciliation ([plan](docs/plan.md)).

## What v0.1 does

- **Ingests** four series from the Bank of Canada (Valet API) and Statistics Canada (WDS): USD/CAD daily exchange rate, the Bank of Canada policy rate, Ontario CPI and the Ontario unemployment rate. Runs are incremental and idempotent: each one re-reads a short lookback window to pick up revisions, and a re-run changes nothing.
- **Keeps the raw responses** byte for byte, with a hash in the run log, so any number can be traced to the file it came from.
- **Models** the data with dbt on DuckDB: staging views, a small star schema (`dim_date`, `dim_indicator`, `fct_observation`) and a monthly table for dashboards, with 57 data tests, a unit test and per-series freshness checks.
- **Runs itself.** GitHub Actions checks every pull request on Linux and Windows, and runs the full pipeline against the live APIs every day.

## Architecture

```mermaid
flowchart LR
    subgraph Sources["Open data APIs"]
        BOC["Bank of Canada<br/>Valet API"]
        STC["Statistics Canada<br/>WDS"]
    end
    BOC --> ING["Python ingestion<br/>(incremental, idempotent)"]
    STC --> ING
    ING --> RAW[("Raw landing<br/>JSON files")]
    ING --> DDB[("DuckDB<br/>raw schema")]
    DDB --> DBT["dbt<br/>staging → marts, tests, freshness"]
    DBT --> MART[("Star schema and<br/>monthly mart")]
    GHA["GitHub Actions<br/>CI on every PR · daily run"] -.-> ING
    ORA[("Oracle Free<br/>legacy source")] -. v1.0 .-> BQ[("BigQuery")]
    ORA -. v1.0 .-> REC["Reconciliation<br/>report"]
    BQ -. v1.0 .-> REC
```

Dotted boxes with "v1.0" are planned, not built.

## Run it

You need [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for the project) and Git. No accounts, keys or cloud services.

```powershell
git clone https://github.com/manuelrpmca/canada-data-migration.git
cd canada-data-migration
uv run cdm run                              # downloads the data, then builds and tests the dbt models
uv run cdm status                           # rows and date range per series
uv run cdm dbt source freshness             # is each series as recent as it should be?
uv run cdm sql "SELECT * FROM marts.mart_monthly_indicators ORDER BY month_start DESC LIMIT 12"
```

The same commands work in PowerShell on Windows and in a macOS or Linux terminal. The warehouse is a single file, `data/warehouse.duckdb`. Run `uv run cdm --help` for every command, and `uv run cdm dbt docs generate` then `uv run cdm dbt docs serve` for the model documentation.

On a VPN or company network, Statistics Canada may answer `403 Forbidden`; turn the VPN off and run again ([troubleshooting](docs/qa/README.md#troubleshooting-errors-seen-on-windows)).

## Results from a real run

All numbers below come from real runs on 2026-11-02, with the command that produced them.

| Command | Where | Result |
| --- | --- | --- |
| `uv run cdm run` on an empty warehouse | Fresh clone, Linux | 4 series `success`: usd_cad 2452 rows (2017-01-03 to 2026-10-30), policy_rate 2551 (2017-01-02 to 2026-10-30), cpi_ontario 117 and unemployment_ontario 117 (2017-01 to 2026-09); dbt PASS=66 WARN=0 ERROR=0; 21 seconds with dependencies already installed |
| `uv run cdm ingest`, run again right after | Same | 30 rows re-read in the lookback window: 0 inserted, 0 updated, 30 unchanged |
| `uv run cdm dbt source freshness` | Same | 4 of 4 PASS |
| `uv run cdm run` from a clean checkout | GitHub Actions, `windows-latest` | 4 series `success`; dbt PASS=66; source freshness 4 of 4 PASS; 0.3 minutes with dependencies already in the uv cache |

The [daily workflow](https://github.com/manuelrpmca/canada-data-migration/actions/workflows/daily.yml) shows every run since, with a summary table and the warehouse as a downloadable artifact.

## Stack and decisions

| Layer | Choice | Why (decision record) |
| --- | --- | --- |
| Sources | Bank of Canada Valet, Statistics Canada WDS | Public, no key, documented ([ADR 0003](docs/decisions/0003-data-sources.md)) |
| Language and tools | Python 3.12, uv, ruff, pytest, httpx | One lock file, one command on any OS ([ADR 0004](docs/decisions/0004-python-toolchain.md)) |
| Ingestion | Raw landing + upsert with a lookback window + run log | Idempotent, auditable, catches revisions ([ADR 0005](docs/decisions/0005-ingestion-pattern.md)) |
| Warehouse | DuckDB (BigQuery sandbox in v1.0) | Free, a single file, nothing to install or host ([ADR 0006](docs/decisions/0006-warehouses.md)) |
| Transformation | dbt Core | Tested, documented SQL models ([ADR 0007](docs/decisions/0007-transformation-with-dbt.md)) |
| Orchestration and CI | GitHub Actions | No servers, visible history, free for public repositories ([ADR 0008](docs/decisions/0008-orchestration-and-ci.md)) |

All decisions: [docs/decisions](docs/decisions/README.md).

## Limits of v0.1

- Four series, one province. Adding a series is one entry in [`config/series.yml`](config/series.yml).
- DuckDB only; no cloud warehouse and no reconciliation yet (v1.0).
- The daily run keeps the warehouse in the GitHub Actions cache. If the cache is evicted, the next run downloads the full history again (about 5,200 rows; it takes seconds).
- Business days are inferred from the days USD/CAD is published; neither API publishes a holiday calendar.
- GitHub pauses scheduled workflows in a public repository after 60 days without activity.
- Alerting is GitHub's email on a failed run.

## Next (v1.0)

Oracle Database Free as a bank-style legacy source loaded with PL/SQL, migration to BigQuery and DuckDB, and a reconciliation report (row counts, control totals and fingerprints per partition) published to GitHub Pages. See the [milestone plan](docs/plan.md).

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
