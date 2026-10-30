# M1. Ingestion

Date closed: open · Owner hours: to be logged

## What was done

- Python project with uv, a lock file, ruff and pytest ([ADR 0004](../decisions/0004-python-toolchain.md)). Dependabot watches the Python dependencies and GitHub Actions.
- `config/series.yml` lists the four v0.1 series ([ADR 0003](../decisions/0003-data-sources.md)).
- One client per source: `src/cdm/sources/valet.py` and `statcan.py`. They share one HTTP helper with timeouts and retries.
- Raw landing, DuckDB upsert, lookback window and run log ([ADR 0005](../decisions/0005-ingestion-pattern.md)).
- CLI commands: `cdm ingest`, `cdm status`, `cdm verify` and `cdm find-vector`.
- Unit tests that never call the network.

## Why it was done this way

- **Retries with back-off and jitter, written by hand** (`src/cdm/http.py`, about 30 lines). Both APIs ask clients to back off, and StatCan answers HTTP 409 while it publishes. A short, tested function is easier to explain than a retry library's settings.
- **Explicit UPDATE + INSERT in one transaction**, not a single `INSERT ... ON CONFLICT`. The same comparison produces the inserted, updated and unchanged counts and changes the data, so the run log cannot disagree with the table. It is also the shape of the Oracle `MERGE` in M4.
- **The table key is `(source, series_key, ref_date)`.** ADR 0005 named `series_id`. The stable key from the config is used instead, because a StatCan vector ID is not known until it is verified, and the vector ID is still stored in its own column.
- **StatCan uses `getDataFromVectorsAndLatestNPeriods`.** It asks for the number of months since the request start. The WDS guide is inconsistent about the parameter names of the date-range method, so this documented method avoids guessing.
- **A series without an identifier is skipped and logged, not guessed.**
- **`cdm find-vector` pads the coordinate to 10 positions.** WDS answered HTTP 406 to `14.2` and accepted `14.2.0.0.0.0.0.0.0.0`, so the CLI now takes only the dimensions a table has.

## Confirmed identifiers (2026-10-30)

Checked with `uv run cdm verify` and `uv run cdm find-vector` against the live APIs ([ADR 0003](../decisions/0003-data-sources.md)). Units were checked against WDS `getCodeSets`.

| Key | Source | Identifier | Title returned by the API | Unit |
| --- | --- | --- | --- | --- |
| `usd_cad` | Valet | `FXUSDCAD` | "USD/CAD": daily average exchange rate of the US dollar in Canadian dollars | Canadian dollars per US dollar, business daily |
| `policy_rate` | Valet | `V39079` | "Target for the overnight rate (business daily)" | Percent, business daily |
| `cpi_ontario` | WDS table 18100004, "Consumer Price Index, monthly, not seasonally adjusted" | vector `41691919`, coordinate `14.2` | "Ontario;All-items" | 2002=100 (UOM 17), monthly |
| `unemployment_ontario` | WDS table 14100287, "Labour force characteristics, monthly, seasonally adjusted and trend-cycle" | vector `2063949`, coordinate `7.7.1.1.1.1` | "Ontario;Unemployment rate;Total - Gender;15 years and over;Estimate;Seasonally adjusted" | Percent (UOM 239), monthly |

All four identifiers were right except for wording: table 14100287 uses "Total - Gender", not "Both sexes", and its title includes "and trend-cycle". The data type dimension is what selects the seasonally adjusted series.

## Measured results

Two runs of `uv run cdm ingest` on 2026-10-30 at 12:07 UTC, from Claude's cloud environment, into an empty DuckDB file. The owner's QA run on Windows 11 is still to come.

| Series | Run 1 received / inserted | Run 2 request start | Run 2 received | Run 2 inserted / updated / unchanged | Rows | First date | Last date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `usd_cad` | 2451 / 2451 | 2026-10-15 | 11 | 0 / 0 / 11 | 2451 | 2017-01-03 | 2026-10-29 |
| `policy_rate` | 2549 / 2549 | 2026-10-14 | 11 | 0 / 0 / 11 | 2549 | 2017-01-02 | 2026-10-28 |
| `cpi_ontario` | 117 / 117 | 2026-06-01 | 4 | 0 / 0 / 4 | 117 | 2017-01-01 | 2026-09-01 |
| `unemployment_ontario` | 117 / 117 | 2026-06-01 | 4 | 0 / 0 / 4 | 117 | 2017-01-01 | 2026-09-01 |

Observed, to handle in M2: `policy_rate` has 101 dates that `usd_cad` does not (2017-01-02 to 2026-10-12, for example 2017-01-02, 2017-02-20, 2017-12-25, which look like Canadian holidays), and `usd_cad` has 3 dates that `policy_rate` does not. A daily join between the two needs an explicit calendar rule.

## What I would say in an interview

"The ingestion is incremental and idempotent. Each run re-reads a short window before the last loaded date, so statistical revisions are picked up. It saves the raw response before parsing, so any load can be replayed. Then it merges on a natural key and logs inserted, updated and unchanged counts per series. Running it twice changes nothing, and a test proves it."

## What I learned / what surprised me

- To be filled in by Manuel at milestone close.
