# QA script: M2 dbt models

Run on your machine after the M2 pull requests are merged. About 15 minutes.

```bash
git pull
uv sync
uv run cdm run                # 1. ingest + dbt build; expected: all models and tests PASS
cd dbt
uv run dbt source freshness   # 2. expected: PASS (or WARN with a clear reason, e.g. a weekend)
uv run dbt docs generate      # 3. builds the docs site
uv run dbt docs serve         # 4. opens the docs in the browser
```

Check:

- [ ] Step 1 ends with zero errors; note the number of models and tests in the M2 note.
- [ ] In the docs site (step 4), the lineage graph shows sources -> staging -> marts.
- [ ] `mart_monthly_indicators` has one row per month, with CPI, unemployment rate, average USD/CAD and the policy rate.
- [ ] Break a test on purpose: insert a duplicate row into the raw table (command given in the M2 note), run `dbt build`, see the `unique` test fail, then run `uv run cdm ingest` and `dbt build` again and see it pass.
- [ ] You can explain why `fct_observation` is long (one row per indicator per date) and the mart is wide.
