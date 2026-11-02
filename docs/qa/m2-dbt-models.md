# QA script: M2 dbt models

Run on your machine after the M2 pull request is merged. About 15 minutes. Commands are for **PowerShell on Windows 11**; they also work in a macOS or Linux terminal.

## One-time setup

Skip what you already have. See [Troubleshooting](README.md#troubleshooting-errors-seen-on-windows) if a command is not recognized.

```powershell
# 1. Install uv (it also installs Python 3.12 for this project)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# 2. Let this window find uv without reopening it
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv --version                 # expected: a version number

# 3. Clone the repository into your home folder (needs Git for Windows: https://git-scm.com/download/win)
cd $HOME
git clone https://github.com/manuelrpmca/canada-data-migration.git
```

The script below starts with `cd $HOME\canada-data-migration`. If you cloned the repository somewhere else, `cd` into that folder instead.

## Script

Run the commands one at a time; the text after `#` is a comment and can be pasted too.

```powershell
cd $HOME\canada-data-migration
git switch main
git pull
uv sync                        # 1. installs dbt-core and dbt-duckdb from the lock file
uv run pytest                  # 2. expected: all tests pass, including the offline dbt build
uv run cdm run                 # 3. ingest + dbt build. Expected: success for the 4 series, then "Done. PASS=66 WARN=0 ERROR=0 ..."
uv run cdm dbt source freshness  # 4. expected: PASS for the four series (WARN only with a clear reason)
uv run cdm dbt docs generate     # 5. builds the docs site into dbt\target
uv run cdm dbt docs serve        # 6. opens the docs in the browser; Ctrl+C to stop
```

Every command runs from the repository folder; there is no `cd dbt`. `uv run cdm dbt <command>` runs any dbt command on this project and warehouse. Turn any VPN off first: Statistics Canada can answer 403 through one (see [Troubleshooting](README.md#troubleshooting-errors-seen-on-windows)).

Look at the mart:

```powershell
uv run cdm sql "SELECT * FROM marts.mart_monthly_indicators ORDER BY month_start DESC LIMIT 13"
```

Break a test on purpose, then let the pipeline repair it:

```powershell
# 7. Overwrite the latest policy rate with an impossible value
uv run cdm sql "UPDATE raw.observations SET value = 99 WHERE series_key = 'policy_rate' AND ref_date = (SELECT max(ref_date) FROM raw.observations WHERE series_key = 'policy_rate')"
uv run cdm run --skip-ingest   # 8. expected: FAIL 1 assert_values_within_plausible_range, ERROR=1
uv run cdm run                 # 9. ingest re-reads the lookback window: policy_rate shows upd 1; build PASS
```

## Check

- [ ] Step 3 ends with `ERROR=0`; write the PASS count in the M2 note.
- [ ] Step 4: four `PASS` lines (one per series).
- [ ] In the docs site (step 6), the lineage graph (button at the bottom right) shows sources -> staging -> marts, and each model has descriptions and tests.
- [ ] The mart query shows one row per month with CPI, its year-over-year change, unemployment rate, average USD/CAD and the policy rate. The latest month can have empty CPI and unemployment: Statistics Canada has not published it yet.
- [ ] Steps 7-9: the test fails, then `cdm run` repairs the value from the API and the build passes. You can explain why (lookback window, ADR 0005).
- [ ] You can explain why `fct_observation` is long (one row per indicator per date) and the mart is wide (one column per indicator).
