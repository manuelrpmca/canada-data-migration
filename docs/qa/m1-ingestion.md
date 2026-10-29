# QA script: M1 Ingestion

Run on your machine after the M1 pull request is merged. About 15 minutes. Commands are for **PowerShell on Windows 11**; they also work in a macOS or Linux terminal.

## One-time setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (it also installs Python 3.12 for this project), then open a new PowerShell window:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Script

```powershell
cd canada-data-migration
git switch main
git pull
uv sync                  # 1. installs the locked environment
uv run ruff check .      # 2. expected: "All checks passed!"
uv run pytest            # 3. expected: all tests pass. Turn Wi-Fi off first: no test needs the network
uv run cdm verify        # 4. Wi-Fi back on. Prints each series' title from the live APIs
uv run cdm ingest        # 5. first run: backfills the four series from 2017-01-01
uv run cdm ingest        # 6. second run: expected ins 0 and upd 0 for every series
uv run cdm status        # 7. rows, first and last date per series, and the last run
```

## Check

- [ ] Step 4 shows the expected title for each series (USD/CAD; target for the overnight rate; CPI all-items Ontario; unemployment rate Ontario).
- [ ] Step 5 shows `success` for all four series with rows received and inserted.
- [ ] Step 6 inserts and updates nothing (idempotency).
- [ ] Step 7 shows four series; the last daily date is a recent business day, the last monthly date is a recent month.
- [ ] `data\raw\` has one JSON file per series per run, and `git status` does not list them.
- [ ] Spot-check one value: pick a date from step 7, compare it with the Bank of Canada or Statistics Canada website, and write the date, value and source page in the M1 note.
- [ ] You can explain the lookback window by reading `request_start` in `src/cdm/pipeline.py`.
