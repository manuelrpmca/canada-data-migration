# 0005. Ingestion pattern: raw landing, upsert, lookback window

- Status: Accepted
- Date: 2026-10-29
- Milestone: M1

## Context

Ingestion must be **incremental** (do not re-download everything every day) and **idempotent** (running it twice produces the same tables, with no duplicates). Published statistics are also **revised**: a month already loaded can change in a later release. A migration project also needs an audit trail: what exactly did the source return, and when?

## Options considered

1. **Full reload every run.** Simplest and naturally idempotent, but not incremental, wasteful against public APIs that ask to be called gently, and it hides the incremental-load skills the project should show.
2. **Append only from the last loaded date.** Incremental, but duplicates on re-runs and misses revisions to past periods.
3. **Land raw responses, then upsert with a lookback window.** Each run asks for data from (last loaded period minus a lookback window) to today, saves the raw response as a file, and merges rows into the warehouse on a natural key.

## Decision

Option 3.

1. **Watermark.** For each series, the next request starts at the latest reference date already loaded minus a lookback window (proposed: 10 business days for daily series, 3 periods for monthly series; tuned in M1 and recorded in `config/series.yml`). An empty table triggers a full backfill from a configured start date.
2. **Raw landing.** The response is saved unchanged to `data/raw/<source>/<series>/<run timestamp>.json` with a content hash. Nothing is parsed before it is saved.
3. **Load.** Rows are parsed into a single long, typed table (`source`, `series_id`, `ref_date`, `value`, plus `ingested_at`, `run_id`, `payload_hash`) and **merged on (`source`, `series_id`, `ref_date`)**: new keys are inserted, changed values are updated, unchanged rows are left alone.
4. **Run log.** Each run writes one row per series to a `run_log` table: rows received, inserted, updated, unchanged, and status. This is the first building block of reconciliation.

## Consequences

- Running ingestion twice in a row inserts and updates nothing the second time; this is a QA check for M1.
- Revisions inside the lookback window are captured; older revisions are not, unless a full backfill is run. That limit is documented in the README.
- Raw files grow slowly (small JSON per series per day). They are git-ignored locally; in CI they are kept as short-lived workflow artifacts.
- The same pattern carries over to Oracle in v1.0: the PL/SQL load package performs the equivalent `MERGE`.
