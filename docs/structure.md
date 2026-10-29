# Repository structure

Proposed layout. Folders appear when the milestone that needs them starts; nothing is created empty "just in case". The milestone that introduces each folder is in brackets.

```text
canada-data-migration/
├── README.md                 # 60-second overview, diagram, one-command run          [M0]
├── LICENSE                   # MIT, code only                                        [M0]
├── CHANGELOG.md              # Keep a Changelog format, one entry per release        [M0]
├── MEMORY.md                 # Working rules and current state, for humans and AI    [M0]
├── .env.example              # Empty keys only; real values live in .env or CI secrets [M0]
├── pyproject.toml            # Project metadata, pinned dependencies, ruff/pytest config [M1]
├── uv.lock                   # Exact, reproducible dependency versions               [M1]
├── config/
│   └── series.yml            # Declarative list of series to ingest (source, id, frequency) [M1]
├── src/cdm/                  # Python package ("cdm" = canada data migration)        [M1]
│   ├── cli.py                # Single entry point: `uv run cdm <command>`
│   ├── settings.py           # Reads config/ and environment variables
│   ├── sources/              # One API client per source: valet.py, statcan.py
│   ├── landing.py            # Writes raw API responses to data/raw/ unchanged
│   ├── load/                 # One loader per target: duckdb.py [M1], oracle.py [M4], bigquery.py [M5]
│   └── reconcile/            # Counts, control totals, fingerprints, HTML report     [M6]
├── dbt/                      # dbt project                                           [M2]
│   ├── models/staging/       # One model per source table: rename, cast, deduplicate
│   ├── models/marts/         # Star schema: dimensions and facts
│   ├── tests/                # Singular data tests
│   └── profiles.yml          # Targets: duckdb (local, CI), bigquery [M5]; no secrets
├── oracle/                   # Legacy source                                         [M4]
│   ├── ddl/                  # Bank-style schema
│   └── plsql/                # Load package (spec and body)
├── docker-compose.yml        # Oracle Database Free container                        [M4]
├── tests/                    # pytest                                                [M1]
│   ├── unit/
│   └── fixtures/             # Recorded API responses so tests never call the network
├── .github/
│   ├── workflows/ci.yml      # Lint, unit tests, dbt build on every PR               [M3]
│   ├── workflows/daily.yml   # Scheduled daily run against the live APIs            [M3]
│   └── dependabot.yml        # Weekly updates for Python deps and Actions            [M1]
├── data/                     # Git-ignored: raw landing files and warehouse.duckdb
└── docs/
    ├── plan.md               # Milestones, dates, hours, exit criteria
    ├── structure.md          # This file
    ├── decisions/            # ADRs, numbered, never rewritten once accepted
    ├── progress/tracker.md   # Live status of every milestone task
    ├── qa/                   # One short QA script per milestone, run on Manuel's machine
    └── notes/                # One "what was done and why" note per milestone
```

## Why this shape

- **`src/` layout.** Tests import the installed package, not files that happen to sit next to them, which catches packaging mistakes early. It is the layout used in the [Python Packaging User Guide tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/).
- **One client per source, one loader per target.** Adding Oracle and BigQuery in Phase 2 means adding files, not editing the ingestion code. The migration story stays visible in the tree.
- **`config/series.yml` instead of hard-coded series.** Adding an indicator is a one-line change that a reviewer can read without reading Python.
- **dbt in its own folder.** dbt has its own project conventions; keeping it apart lets the same models run against DuckDB and BigQuery by switching target.
- **Raw landing files are kept.** Every load can be replayed and audited from exactly what the API returned (see [ADR 0005](decisions/0005-ingestion-pattern.md)).
- **No `notebooks/` folder.** Exploration happens outside the repo; what is committed is the pipeline.
