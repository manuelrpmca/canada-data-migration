# QA script: M4 Governed Oracle source

Run on **Ubuntu 24.04, in a terminal**, after the M4 pull request is merged. About 40 minutes the first time: 10 to install Docker, 5 for the Oracle download, 20 for the checks. Rules: [QA scripts](README.md#rules-for-every-script-ubuntu).

## Before you start

- **Turn the VPN off** (Statistics Canada answers 403 through it, see [troubleshooting](README.md#troubleshooting-ubuntu)).
- **Free resources:** Oracle needs about 2 GiB of free memory while it runs and about 7 GB of free disk for the image (Docker keeps it under `/var/lib/docker`, on the system disk). Check with the two commands in Part 1.
- **Port 1521** must be free. If another Oracle database runs on this computer, stop it first.
- **Nothing is exposed to the network.** The container listens on `127.0.0.1` only (this computer), so other services and the firewall are not affected. It does not start on its own at boot: only `uv run cdm oracle up` starts it.
- **No account and no cost.** Docker comes from Ubuntu's own packages (Docker Engine), not Docker Desktop; no Docker account is needed.

What was verified before this script was handed over, so a failure here is news: every command in Part 2 run from a fresh clone on Ubuntu 24.04, with Docker, against the live APIs; the `oracle` CI job green (it starts Oracle with the same `uv run cdm oracle up`). Not verified: the Docker install in Part 1 on your computer, because Claude's environment already has Docker.

## Part 1. One-time setup

If this computer has never run the project, do the [one-time setup](README.md#one-time-setup-on-ubuntu-copy-into-each-script) first (Git, uv and the clone).

Check space and memory, then install Docker:

```bash
df -h /                                               # free disk on the system disk: the "Avail" column must show 7G or more
free -h                                               # memory: the "available" column on the "Mem:" line must show 2.0Gi or more
sudo apt install -y docker.io docker-compose-v2       # sudo: installs Docker Engine and Docker Compose from Ubuntu. Expected: "Setting up docker.io ..."
systemctl is-active docker                            # expected: "active" (the Docker service runs in the background and starts with the computer)
sudo usermod -aG docker $USER                         # sudo: adds your user to the "docker" group, so you can use Docker without sudo. Expected: no output
```

Now **log out of Ubuntu and log in again** (top-right menu, Power Off / Log Out, Log Out). A group change only applies to sessions started after it. Then open a terminal:

```bash
groups                                                # expected: the list includes "docker"
docker run --rm hello-world                           # runs a tiny test container and removes it. Expected: "Hello from Docker!"
docker compose version                                # expected: "Docker Compose version v2.x" or newer
```

## Part 2. In the terminal

```bash
cd ~/Documents/projects/canada-data-migration       # the repository folder; the only cd in this script
git checkout main                                   # expected: "Already on 'main'" or "Switched to branch 'main'"
git pull                                            # expected: the M4 files arrive (docker-compose.yml, oracle/, src/cdm/load/oracle.py)
uv run pytest                                       # expected: "passed" and "12 skipped" (the Oracle tests, run below), no "failed"
uv run cdm oracle up                                # expected: the first time, a 1.3 GB download, then "Container cdm-oracle Healthy", six "setup" lines and "Oracle ready: owner CDM_OWNER, loader CDM_LOADER, read-only CDM_MIGRATION."
uv run cdm run                                      # expected: 4 series "success", then "PASS=" with "ERROR=0"
uv run cdm oracle load                              # expected: one line per series, "loaded" 1 or more, no "FAILED"
uv run cdm oracle load                              # expected: "loaded" 0 on every line, "already" equal to "files": a second load changes nothing
uv run cdm oracle status                            # expected: 4 series with "periods" in the hundreds or thousands and a "last load" time
uv run cdm oracle compare                           # expected: 4 lines ending in "match": Oracle and DuckDB hold the same rows and totals
uv run cdm oracle sql "select column_name, column_classification, column_description from data_dictionary where table_name = 'OBSERVATION_REVISION' order by column_id"   # expected: 7 rows, each with Public or Internal and a description
uv run cdm oracle sql "delete from load_audit"      # expected: "Oracle error: ORA-41900: missing DELETE privilege": the migration user is read-only
uv run cdm oracle sql "select count(*) from observation_as_of(timestamp '2026-01-01 00:00:00')"   # expected: 0. Nothing was known before your first load
CDM_ORACLE_TESTS=1 uv run pytest -m oracle          # runs the Oracle integration tests (CDM_ORACLE_TESTS=1 turns them on for this command only). Expected: "12 passed"
uv run cdm oracle down                              # expected: "Container cdm-oracle Removed". The data stays in the Docker volume for next time
```

- [ ] Every expected result matched. If one did not, paste that command's full output in the chat and stop there.

## Part 3. Read the design (10 minutes)

- [ ] [ADR 0009](../decisions/0009-legacy-source-and-reconciliation.md): the accounts, the revision history and why the load is not a single `MERGE` make sense to you.
- [ ] [M4 note](../notes/m4-oracle-source.md): you could explain the "what was known on day X" query in an interview.

Done. Say "QA M4 OK" in the chat, or paste the first command whose result did not match.
