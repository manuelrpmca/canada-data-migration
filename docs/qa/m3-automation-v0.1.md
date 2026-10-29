# QA script: M3 Automation and v0.1

Run after the M3 pull requests are merged and before approving the `v0.1` tag. About 20 minutes.

## CI and schedule

- [ ] The last pull request shows the CI check green, with lint, tests and `dbt build` steps.
- [ ] Actions > `daily` > Run workflow (manual run) finishes green; the DuckDB file and run log appear as artifacts.
- [ ] The scheduled run has run at least once on its own and is green.
- [ ] The CI badge on the README is green.

## Fresh-machine test (the "one command" promise)

In a new folder, ideally on a second machine or a fresh user account:

```bash
git clone https://github.com/manuelrpmca/canada-data-migration.git
cd canada-data-migration
uv run cdm run      # the one command from the README; expected: completes with all tests passing
```

- [ ] It works with no steps other than installing uv.
- [ ] Time it and write the real duration in the M3 note (it may go in the README).

## README (60-second test)

Ask someone who has not seen the project to read the README for 60 seconds, then answer:

- [ ] What problem does it solve?
- [ ] How do you run it?
- [ ] What are its limits?

## Release

- [ ] CHANGELOG has a `0.1.0` section dated today.
- [ ] Every number in the README comes from a real run (no estimates).
- [ ] The "Work in progress" banner is replaced by the v0.1 status.
- [ ] You approve the tag and release notes (they are public).
