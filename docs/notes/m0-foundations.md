# M0. Foundations

Date closed: open · Owner hours: to be logged

## What was done

- Proposed the repository structure ([structure.md](../structure.md)).
- Wrote nine ADRs: eight accepted on merge (process, scope, data sources, Python toolchain, ingestion pattern, warehouses, dbt, GitHub Actions) and one proposed for Phase 2 (Oracle and reconciliation). See the [index](../decisions/README.md).
- Wrote the [milestone plan](../plan.md) with dates, hour estimates, exit criteria and a QA script per milestone.
- Added the MIT license, `.gitignore`, `.env.example`, `MEMORY.md`, `CHANGELOG.md` and this tracker.

## Why it was done this way

- **Plan before code.** The ADRs fix the boundaries (open data only, no paid services, v0.1 without cloud) so the build milestones are small and predictable.
- **Two releases.** v0.1 is useful on its own and runs anywhere; v1.0 adds the migration story ([ADR 0002](../decisions/0002-scope-and-non-goals.md)).
- **Sandbox limits read first.** The BigQuery sandbox does not allow DML and expires tables after 60 days, which changes the load design for v1.0 ([ADR 0006](../decisions/0006-warehouses.md)). Better to know now than in M5.

## Measured results

None yet. No numbers are published until a real run produces them.

## What I would say in an interview

"Before writing code I wrote down the scope and every tool choice as short decision records, including what I chose not to use and why. For example, I kept Airflow out because a daily batch of a few API calls does not need a scheduler server; GitHub Actions gives me CI and a schedule with nothing to operate."

## What I learned / what surprised me

- To be filled in by Manuel at milestone close.
