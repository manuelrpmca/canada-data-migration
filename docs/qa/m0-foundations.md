# QA script: M0 Foundations

Run after the M0 pull request is merged. About 20 minutes. Tick each box; anything unticked goes into the tracker as a follow-up.

## Repository

- [ ] `README.md` shows the "Work in progress" banner and renders the Mermaid diagram on GitHub.
- [ ] `LICENSE` is MIT with your name and 2026.
- [ ] Settings > Code security: **Secret scanning** and **Push protection** are on.
- [ ] Settings > Code security: **Dependabot alerts** are on.
- [ ] Settings > Rules (or Branches): `main` requires a pull request before merging.
- [ ] Clone fresh and confirm secrets cannot be committed by accident:

  ```bash
  git clone https://github.com/manuelrpmca/canada-data-migration.git
  cd canada-data-migration
  cp .env.example .env
  git status --short   # expected: no output (.env is ignored)
  ```

## Understanding (interview check)

Without opening the files, explain out loud in one or two sentences each:

- [ ] Why v0.1 uses DuckDB and not BigQuery ([ADR 0006](../decisions/0006-warehouses.md)).
- [ ] What "idempotent" means for this pipeline and how the lookback window handles revisions ([ADR 0005](../decisions/0005-ingestion-pattern.md)).
- [ ] Why there is no Airflow in v1.0 ([ADR 0008](../decisions/0008-orchestration-and-ci.md)).

## Public profiles (Phase 0)

- [ ] GitHub profile README is live and uses the headline "Senior Data Engineer".
- [ ] Microsoft Learn transcript link opens without signing in.
- [ ] Credly and Tableau Public profiles exist and link back to the website.
- [ ] LinkedIn Featured links the website.
- [ ] dbt Fundamentals badge earned (needed before M2).
