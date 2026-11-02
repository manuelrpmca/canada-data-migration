# QA script: M3 Automation and v0.1

Run after the M3 pull request is merged and before approving the `v0.1` tag. About 20 minutes: 5 in the browser, 10 in PowerShell, 5 for the README.

Before you start: **turn the VPN off** (Statistics Canada answers 403 through it, see [troubleshooting](README.md#troubleshooting-errors-seen-on-windows)).

What was verified before this script was handed over, so a failure here is news: CI green on `ubuntu-latest` and `windows-latest`; the daily workflow run against the live APIs on GitHub; `uv run cdm run` from a clean checkout on `windows-latest`; the PowerShell part below run from a fresh clone on Linux (Claude has no Windows machine; the Windows CI jobs stand in for it).

## Part 1. In the browser (GitHub)

1. Open the merged pull request. Expected: four green checks, `test (ubuntu-latest)`, `test (windows-latest)`, `run` and `windows-fresh-run`.
2. Open **Actions > daily > Run workflow**, keep branch `main`, click **Run workflow**. Expected after about one minute: green. Open the run: the summary shows a table with four series and today's date as the last run, and an artifact named `daily-<number>` is listed.
3. The README on the repository home page shows two badges, `ci` and `daily`, both green.
4. The next day after 15:00 UTC (10:00 or 11:00 in Toronto), **Actions > daily** shows a run started by `schedule`, green, with "Warehouse restored from cache: warehouse-v1-..." in its summary.

## Part 2. In PowerShell (your machine)

If this machine has never run the project, do the [one-time setup](README.md#one-time-setup-copy-into-each-script) first.

```powershell
cd $HOME\canada-data-migration
git checkout main
git pull                                  # expected: the M3 files arrive (.github/workflows/ci.yml, daily.yml)
uv run pytest                             # expected: 56 passed
uv run cdm run                            # expected: 4 series "success", then "Done. PASS=66 WARN=0 ERROR=0"
uv run cdm dbt source freshness           # expected: 4 of 4 PASS
uv run cdm dbt --version                  # expected: "Core:" and an installed dbt version (this failed before M3)
uv run cdm --db nowhere.duckdb status     # expected: "No warehouse at nowhere.duckdb." and how to create it
```

- [ ] Every expected result matched. If one did not, paste that command's full output in the chat and stop there.

## Part 3. README (60-second test)

Ask someone who has not seen the project to read the README for 60 seconds, then answer:

- [ ] What problem does it solve?
- [ ] How do you run it?
- [ ] What are its limits?

## Part 4. Release (you approve; nothing public happens before)

- [ ] Every number in the README comes from a real run (dates and commands are in the table).
- [ ] The README status line says v0.1, not "Work in progress".
- [ ] Say "OK v0.1" in the chat. Claude then opens the release pull request (CHANGELOG `0.1.0` dated that day, version 0.1.0, your QA results) with the release notes in it. After you merge it, you publish the release yourself: **Releases > Draft a new release**, tag `v0.1` on `main`, paste the notes, **Publish**. Publishing is the public step, so it stays in your hands.
