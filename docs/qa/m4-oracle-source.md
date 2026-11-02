# QA script: M4 Governed Oracle source

Run after the M4 pull request is merged. About 45 minutes the first time: 20 to install Docker Desktop (one restart may be needed), 5 for the Oracle download, 20 for the checks.

## Before you start

- **Turn the VPN off** (Statistics Canada answers 403 through it, see [troubleshooting](README.md#troubleshooting-errors-seen-on-windows)).
- **Free resources:** Oracle needs about 2 GiB of free memory while it runs and about 7 GB of free disk for the image. Docker Desktop itself needs Windows 11 with virtualization turned on (it is on by default on most PCs).
- **Docker Desktop costs nothing for personal use** under Docker's subscription terms, which the installer shows; read them before accepting. This project needs no paid plan and no Docker account.
- **Port 1521** must be free. If another Oracle database runs on this PC, stop it first.

What was verified before this script was handed over, so a failure here is news: every command in Part 2 run from a fresh clone on Linux, with Docker, against the live APIs; the `oracle` CI job green (it starts Oracle with the same `uv run cdm oracle up`); the other tests green on `windows-latest`. Not verified: Docker Desktop on Windows, because Claude has no Windows machine and GitHub's Windows runners cannot run Linux containers. That is what Part 1 and Part 2 check.

## Part 1. One-time setup

If this machine has never run the project, do the [one-time setup](README.md#one-time-setup-copy-into-each-script) first (uv and the clone).

Install Docker Desktop:

```powershell
winget install -e --id Docker.DockerDesktop   # expected: "Successfully installed". Accept the prompts.
```

Then, outside PowerShell:

1. If the installer asks to restart Windows, restart.
2. Open **Docker Desktop** from the Start menu. Accept the terms. Skip the sign-in and the survey (no account is needed).
3. Wait until the bottom-left corner says **Engine running**.
4. Close PowerShell and open a **new** PowerShell window, so it finds the `docker` command.

```powershell
docker version          # expected: a "Client" section and a "Server: Docker Desktop" section
```

If `winget` is not available, download the installer from https://docs.docker.com/desktop/setup/install/windows-install/ and run it with the default options (WSL 2).

## Part 2. In PowerShell

Docker Desktop must say **Engine running** before you start.

```powershell
cd $HOME\canada-data-migration
git checkout main
git pull                                # expected: the M4 files arrive (docker-compose.yml, oracle\, src\cdm\load\oracle.py)
uv run pytest                           # expected: "passed" and "12 skipped" (the Oracle tests, run below), no "failed"
uv run cdm oracle up                    # expected: the first time, a 1.3 GB download, then "Container cdm-oracle Healthy", six "setup" lines and "Oracle ready: owner CDM_OWNER, loader CDM_LOADER, read-only CDM_MIGRATION."
uv run cdm run                          # expected: 4 series "success", then "PASS=" with "ERROR=0"
uv run cdm oracle load                  # expected: one line per series, "loaded" 1 or more, no "FAILED"
uv run cdm oracle load                  # expected: "loaded" 0 on every line, "already" equal to "files": a second load changes nothing
uv run cdm oracle status                # expected: 4 series with "periods" in the hundreds or thousands and a "last load" time
uv run cdm oracle compare               # expected: 4 lines ending in "match": Oracle and DuckDB hold the same rows and totals
uv run cdm oracle sql "select column_name, column_classification, column_description from data_dictionary where table_name = 'OBSERVATION_REVISION' order by column_id"   # expected: 7 rows, each with Public or Internal and a description
uv run cdm oracle sql "delete from load_audit"   # expected: "Oracle error: ORA-41900: missing DELETE privilege": the migration user is read-only
uv run cdm oracle sql "select count(*) from observation_as_of(timestamp '2026-01-01 00:00:00')"   # expected: 0. Nothing was known before your first load
$env:CDM_ORACLE_TESTS = "1"
uv run pytest -m oracle                 # expected: "12 passed"
uv run cdm oracle down                  # expected: "Container cdm-oracle Removed". The data stays in the Docker volume for next time
```

- [ ] Every expected result matched. If one did not, paste that command's full output in the chat and stop there.

## Part 3. Read the design (10 minutes)

- [ ] [ADR 0009](../decisions/0009-legacy-source-and-reconciliation.md): the accounts, the revision history and why the load is not a single `MERGE` make sense to you.
- [ ] [M4 note](../notes/m4-oracle-source.md): you could explain the "what was known on day X" query in an interview.

Done. Say "QA M4 OK" in the chat, or paste the first command whose result did not match.
