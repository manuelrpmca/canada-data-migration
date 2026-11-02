# M2. dbt models

Date closed: open · Owner hours: to be logged

## What was done

- dbt Core project in `dbt/` with a DuckDB target that reads the warehouse written by `cdm ingest` ([ADR 0007](../decisions/0007-transformation-with-dbt.md)). `dbt/profiles.yml` holds no secrets.
- Sources with freshness checks, one per series: warn after 5 days and error after 10 for daily series; warn after 85 days and error after 120 for monthly series.
- Staging views: `stg_observations`, `stg_series`, `stg_run_log`. Marts (tables): `dim_date`, `dim_indicator`, `fct_observation`, `mart_monthly_indicators`. Seed `source_publishers` with the licence and attribution text per source.
- 57 data tests (generic and 5 singular) and 1 dbt unit test for the mart's rules.
- `uv run cdm run` = ingest + `dbt build`, called through dbt's Python API (no shell or `make`, so it works the same on Windows). `uv run cdm sql "<statement>"` runs one statement for QA.
- `cdm ingest` now writes `raw.series`, a snapshot of `config/series.yml`, so dbt reads indicator metadata from one place.
- An offline pytest builds the dbt project on a synthetic warehouse, and checks that a bad value makes the build fail.

## Why it was done this way

- **Indicator metadata comes from the config, not a second copy.** `dim_indicator` reads `raw.series`, written from `config/series.yml` on every ingest. A seed with the same list would drift from the config.
- **Business days are inferred, not hard-coded.** Neither API publishes a holiday calendar. M1 showed the policy rate has a value on every weekday, holidays included, while USD/CAD is published only on Bank of Canada business days. So `dim_date.is_business_day` is "weekday with a USD/CAD rate", and null after the last rate, where the answer is not known yet.
- **The policy rate in the mart is the rate in effect at month end,** found as the latest observation on or before the last day of the month. Carrying it forward covers the few weekdays with no value in Valet (2022-08-02 and 2026-04-23 in the data loaded on 2026-11-01).
- **Freshness is checked per series.** One check over the whole table would pass while one series stalls. Each check reads `raw.observations` through a filter, and the age is measured on the reference date, so it says whether the data is current, not only whether the job ran. The thresholds are planning estimates from the publication pattern (business days; the following month for Statistics Canada) and should be adjusted if they warn on a normal day.
- **Staging deduplicates even though DuckDB enforces the key,** because BigQuery (M5) does not enforce keys and the model must give the same guarantee on both.
- **Adapter-specific SQL is in a macro** (`date_spine`), so the BigQuery target in M5 adds one implementation instead of editing models.

## Measured results

Run on 2026-11-01 around 22:50 UTC in Claude's cloud environment, on a warehouse rebuilt from empty with `uv run cdm ingest`. 

Owner's QA run on Windows 11, 2026-11-02 around 15:05 UTC (PowerShell, VPN off):

| Command | Result |
| --- | --- |
| `uv run pytest` | 42 passed (before PRs #6 and #7 added three tests) |
| `uv run cdm run` | 4 series `success`; dbt PASS=66 WARN=0 ERROR=0 |
| `uv run dbt source freshness` (from `dbt\`) | 4 of 4 PASS |
| `uv run cdm dbt docs generate`, `uv run cdm dbt docs serve` | Catalog written; docs served at http://localhost:8080 |

Found during the run and fixed: Statistics Canada answers 403 through the owner's VPN; `cdm` failed when run from `dbt\`; plain `dbt` failed outside `dbt\`. See the [QA troubleshooting table](../qa/README.md#troubleshooting-errors-seen-on-windows).

| Command | Result |
| --- | --- |
| `uv run cdm ingest` (empty warehouse) | usd_cad 2452 rows (2017-01-03 to 2026-10-30), policy_rate 2550 (2017-01-02 to 2026-10-29), cpi_ontario 117 and unemployment_ontario 117 (2017-01-01 to 2026-09-01) |
| `uv run cdm run` | 1 seed, 7 models, 57 data tests, 1 unit test: PASS=66 WARN=0 ERROR=0, about 3 seconds for dbt |
| `uv run dbt source freshness` | 4 of 4 PASS |
| Latest policy rate set to 99, then `uv run cdm run --skip-ingest` | `assert_values_within_plausible_range` FAIL 1, ERROR=1 |
| `uv run cdm ingest --series policy_rate`, then `cdm run --skip-ingest` | ins 0, upd 1, same 10; PASS=66 |
| `marts.dim_date` | 3652 days (2017-2026): 2452 business days, 113 weekday holidays, 62 days after the last USD/CAD rate |
| `marts.mart_monthly_indicators` | 118 months, 2017-01 to 2026-10; October 2026 has no CPI or unemployment yet |

Plausible-range bounds in the singular test are sanity limits, not published thresholds. The loaded data stays well inside them: USD/CAD 1.204 to 1.4603, policy rate 0.25 to 5.0, Ontario CPI 130.8 to 170.3, Ontario unemployment rate 5.0 to 14.2.

## QA retrospective (2026-11-02)

The models passed on the first real run, but the owner's QA run hit seven problems in about 30 minutes. None was a defect in the models; all were in setup, environment or instructions.

| Problem | Root cause | Prevention now in place |
| --- | --- | --- |
| Repository not cloned; `uv` not installed | QA script assumed the M1 setup was done | One-time setup block in every script ([qa/README.md](../qa/README.md)) |
| `uv` not found right after install | Installer updates PATH only for new windows | PATH line in the setup block |
| StatCan HTTP 403 | Owner's VPN; never tested off Claude's network | VPN warning in the script; troubleshooting row; clearer error planned for M3 |
| `cdm` failed inside `dbt\`; `dbt` failed outside it | Commands depended on the current folder | `cdm` finds the repository root; `cdm dbt` runs dbt from anywhere |
| `cdm dbt` "invalid choice" | Guide changed and merged during the run; chat mixed old and new commands | Handoff protocol: no changes during QA, one follow-up PR after |

Lesson: verification happened only on Linux, and the instructions were written, not executed. From M3, every QA script is run from a fresh clone before handoff, and CI also runs on Windows ([MEMORY.md](../../MEMORY.md), "Working agreement").

## What I would say in an interview

"dbt turns the raw observations into a small star schema: a long fact table with one row per indicator per date, a calendar and an indicator dimension, and one wide monthly table for the dashboard. Every model has tests, including business rules like 'no gaps in monthly series' and 'values in a plausible range'. The demo I like: I corrupt a value, the build fails, and the next ingest repairs it because it re-reads a lookback window."

## What I learned / what surprised me

- To be filled in by Manuel at milestone close.
