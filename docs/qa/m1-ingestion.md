# QA script: M1 Ingestion

Run on your machine after the M1 pull requests are merged. About 15 minutes. Requires [uv](https://docs.astral.sh/uv/) and internet access.

```bash
git pull
uv sync                         # 1. installs the locked environment
uv run ruff check .             # 2. expected: "All checks passed!"
uv run pytest                   # 3. expected: all tests pass; disconnect Wi-Fi first to prove no test needs the network
uv run cdm ingest               # 4. first run: backfills the four series
uv run cdm ingest               # 5. second run: expected 0 inserted and 0 updated for every series
uv run cdm status               # 6. prints row count, first and last reference date per series, and the last run log
```

Check:

- [ ] Step 4 prints rows received / inserted / updated / unchanged per series.
- [ ] Step 5 inserts and updates nothing (idempotency).
- [ ] Step 6 shows four series; the last daily date is a recent business day, the last monthly date is a recent month.
- [ ] `data/raw/` contains one JSON file per series per run; `git status` does not show them.
- [ ] Spot-check one value: pick a date in `cdm status` and compare with the Bank of Canada or Statistics Canada website. Write the date and value in the M1 note.
- [ ] You can explain the watermark and lookback logic by reading `src/cdm/` for five minutes.
