# M4. Governed Oracle source

Date: 2026-11-02 (pull request #12; closes after the owner's QA on Windows 11)

## What was done

- Oracle Database Free 23ai in Docker, started with one command, `uv run cdm oracle up`, which also creates random passwords in the git-ignored `.env` and builds the schema ([ADR 0009](../decisions/0009-legacy-source-and-reconciliation.md), now accepted).
- A schema in the style of a governed system of record in a regulated organization (banks, insurers, public sector): reference tables, every API response kept as received with its hash, effective-dated revisions, a load audit, a data dictionary with a classification per column, and three accounts with separate duties. The features are inspired by common practice; no compliance with any regulation is claimed.
- A PL/SQL package, `cdm_load`, that parses each landed response with `JSON_TABLE` and applies it in one transaction.
- `cdm oracle load | status | sql | compare | down`, integration tests against a real Oracle, and an `oracle` CI job.

## Why it was done this way

- **Revisions are closed and opened, not merged.** Statistics Canada and the Bank of Canada sometimes revise published values; the ingestion re-reads a lookback window to catch them ([ADR 0005](../decisions/0005-ingestion-pattern.md)). DuckDB keeps only the latest value. In Oracle a changed value closes the current row (`known_to`) and opens a new one (`known_from`), so `observation_as_of(timestamp)` answers "what did we know on day X", which is what an auditor or a model validator asks. A unique index on open rows makes "two current values for one period" impossible, not just unlikely.
- **Python moves bytes, PL/SQL owns the rules.** Python sends the file exactly as landed; parsing, the out-of-order check and the history live in the database, next to the data they protect, and are the same whoever calls them.
- **Least privilege you can test.** The owner account cannot sign in at all (schema-only, reached through a proxy connection for DDL). The loader can execute the package and nothing else, so it cannot read or delete tables directly. The migration account M5 will use can only read. Tests try the forbidden statements and expect Oracle to refuse them.
- **Failures leave evidence.** A failed load rolls back its data but its audit row is written in an autonomous transaction, so the attempt is still visible.
- **The dictionary comes from the catalog.** Descriptions are `COMMENT`s and classifications are 23ai annotations on the columns themselves; setup copies them into `DATA_DICTIONARY` and a test fails if any column lacks either. The first design was a view over the catalog, but Oracle refuses to let a schema re-grant catalog views to a role (ORA-01720); finding that took one setup run.
- **The image.** `gvenzl/oracle-free` `slim-faststart` ships with the database created, so it is ready in seconds rather than minutes, which is what made a CI job affordable. It is pinned by digest.
- **CI runs the same command as the QA script.** The `oracle` job starts the container with `uv run cdm oracle up`, not with a hand-written service container, so the command the owner runs is tested on every pull request. It runs on Linux only: GitHub's Windows runners cannot run Linux containers.

## Measured results

Claude's environment (Linux, Docker 29.9), 2026-11-02, live APIs:

| Command | Result |
| --- | --- |
| `docker run` of the image (before writing any code) | Ready in 39 seconds; 2.1 GiB of memory; 1.3 GB download, 6.5 GB on disk |
| `uv run cdm oracle up` (image already downloaded, empty volume) | Healthy and set up in 21 seconds |
| `uv run cdm ingest`, then `uv run cdm oracle load` | 4 files loaded: usd_cad 2453 periods, policy_rate 2551, cpi_ontario 117, unemployment_ontario 117; 2 StatCan entries per series before the 2017-01-01 start date skipped |
| `uv run cdm oracle load` again | 0 loaded, 4 already loaded |
| Second `cdm ingest` and `cdm oracle load` | 1 new file per series, 0 inserted, 0 revised; every period unchanged |
| `uv run cdm oracle compare` | 4 of 4 `match` (rows, first and last period, sum of values) |
| `uv run cdm oracle sql "delete from load_audit"` | `ORA-41900: missing DELETE privilege` |
| `uv run pytest -m oracle` (with `CDM_ORACLE_TESTS=1`) | 12 passed |

GitHub Actions, first run of the `oracle` job (PR #12): image pulled in about 45 seconds, container healthy 6 seconds after start, 1.98 GiB of memory, 12 tests passed, whole job 78 seconds.

No real revision has been captured yet: both runs above were on the same day. The revision path is covered by a test that loads a recorded response and then an edited copy.

## What I would say in an interview

"I modelled the legacy source the way a regulated organization would keep it: the database never forgets a published value, it records when each value was known, and you can ask it what we knew on any date. Loads go through a PL/SQL package that the loader account can execute but nothing else, the migration account can only read, and every load attempt, including failures, is audited. All of it runs in Docker with one command and is tested in CI against a real Oracle on every pull request."
