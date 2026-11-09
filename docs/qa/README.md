# QA scripts

One script per milestone, run by the owner after the milestone's pull requests are merged.

- **From M4 on (2026-11-09): Ubuntu 24.04, in a terminal (bash).** The owner's main computer moved to Ubuntu.
- **M0 to M3: Windows 11, in PowerShell.** Those scripts passed on Windows and stay as written, as a record. Their setup and troubleshooting are in [Windows (scripts M0 to M3)](#windows-scripts-m0-to-m3).

CI keeps testing on both `ubuntu-latest` and `windows-latest`, so the project stays portable.

## Rules for every script (Ubuntu)

Anyone writing or changing a QA script follows these rules, so a script runs top to bottom in a terminal on Ubuntu with no guessing:

1. **bash syntax** in code blocks (```` ```bash ````), **one command per line**, ready to copy and paste. No `make`.
2. **Every command explains itself:** a `#` comment after it says what it does the first time it appears and what result to expect, so the owner can check it worked. Terms new to a Windows user (`~`, `sudo`, `PATH`, groups) are explained the first time a script uses them.
3. **No text editors.** Never "open the file in nano and change...". A file change is a single command (`sed -i`, `tee`, `cat <<'EOF'`) or is done in the repository by Claude.
4. **`sudo` is flagged.** A command that needs `sudo` (administrator rights, asks for the owner's password) says so in its comment and why it needs it. Only installs and Docker setup need it; no project command does.
5. **Self-contained.** A script that runs commands starts with the [one-time setup](#one-time-setup-on-ubuntu-copy-into-each-script) below, copied as is, so it works on a machine that has never run the project.
6. **One folder for the whole script.** The first command is `cd ~/Documents/projects/canada-data-migration`, and no later command changes folder. dbt runs through `uv run cdm dbt <command>`, never `cd dbt` + `uv run dbt`.
7. **Quoting:** SQL passed to `cdm sql` or `cdm oracle sql` goes in double quotes, with single quotes inside for strings.
8. **New tools** need an install line and a check line (for example `docker --version`).
9. **Restart from the top after any merge.** If a pull request is merged while you are running a script, start again from its first line: `git pull` brings the change to your machine, and a command added by that change does not exist until then.
10. **Links** to the repository are full GitHub URLs (https://github.com/manuelrpmca/canada-data-migration), not `owner/repo`.
11. Every new error the owner hits goes into the [troubleshooting table](#troubleshooting-ubuntu) in the same pull request as the fix.

## One-time setup on Ubuntu (copy into each script)

`~` is your home folder (`/home/<your user>`). `sudo` runs a command as administrator and asks for your password once.

```bash
sudo apt update                       # sudo: refreshes the list of Ubuntu packages. Expected: "Reading package lists... Done"
sudo apt install -y git curl          # sudo: installs Git and curl if missing. Expected: "... is already the newest version" or "Setting up ..."
git --version                         # expected: "git version 2.x"
curl -LsSf https://astral.sh/uv/install.sh | sh    # installs uv (it also installs Python 3.12 for this project) in ~/.local/bin. Expected: "everything's installed!"
export PATH="$HOME/.local/bin:$PATH"  # lets this terminal find uv without reopening it (PATH = the folders searched for commands)
uv --version                          # expected: "uv 0.x.y"
mkdir -p ~/Documents/projects         # creates the projects folder if it does not exist. Expected: no output
git clone https://github.com/manuelrpmca/canada-data-migration.git ~/Documents/projects/canada-data-migration   # expected: "Cloning into ..." and "done"
```

If the repository is already cloned there, skip the last line. If it is cloned somewhere else, replace `~/Documents/projects/canada-data-migration` in the scripts with that folder.

## Troubleshooting (Ubuntu)

| Error | Cause | Fix |
| --- | --- | --- |
| `cd: /home/<you>/Documents/projects/canada-data-migration: No such file or directory` | The repository is not cloned there | Run the last two lines of the setup, or `cd` to where it is cloned |
| `fatal: not a git repository` | The terminal is not inside the repository folder | `cd ~/Documents/projects/canada-data-migration` |
| `uv: command not found` | uv is not installed, or was installed in this terminal and PATH is stale | `export PATH="$HOME/.local/bin:$PATH"`, then `uv --version`. A new terminal finds it on its own |
| `curl: command not found` | curl is not installed by default on Ubuntu Desktop | `sudo apt install -y curl` |
| `cdm: error: argument command: invalid choice: ...` | The pull request that added the command is merged on GitHub but not pulled to this machine | `git pull`, then run the command again |
| `403 Forbidden` from `www150.statcan.gc.ca` in `cdm ingest` or `cdm run` (Bank of Canada works) | Statistics Canada blocks requests from some VPN exit addresses; seen 2026-11-02 on Windows | Turn the VPN off and run `uv run cdm run` again. To check: open https://www150.statcan.gc.ca/t1/wds/rest/getCodeSets in the browser; JSON means the network is fine |
| `Docker is not installed or not on PATH` from `cdm oracle up`, or `docker: command not found` | Docker is not installed; listed in advance for M4, not seen yet | Part 1 of the [M4 script](m4-oracle-source.md), then `docker --version` |
| `permission denied while trying to connect to the Docker daemon socket`, or `cdm` says your user cannot use Docker | Your user was added to the `docker` group, but this login session started before that; listed in advance for M4, not seen yet | Log out of Ubuntu and log in again, then `docker run --rm hello-world` |
| `Docker is installed but not running` from `cdm oracle ...` | The Docker service is stopped; listed in advance for M4, not seen yet | `sudo systemctl start docker` (sudo: starts a system service), then `systemctl is-active docker` must say `active` |
| `Bind for 127.0.0.1:1521 failed: port is already allocated` from `cdm oracle up` | Another program (often another Oracle install) uses port 1521; listed in advance for M4, not seen yet | Stop that program, or `printf 'ORACLE_PORT=1522\nORACLE_DSN=localhost:1522/FREEPDB1\n' >> .env`, then `uv run cdm oracle up` again |
| `Oracle error: DPY-6005: cannot connect to database` | The Oracle container is stopped (for example after a restart); listed in advance for M4, not seen yet | `uv run cdm oracle up`; it keeps the data |
| `code 404, message File not found` for `getIcon(...)` while `cdm dbt docs serve` runs | A cosmetic request from dbt's docs page | Harmless; the docs work. Stop the server with Ctrl+C |

## Windows (scripts M0 to M3)

These rules applied to the M0 to M3 scripts, which ran in PowerShell on Windows 11: PowerShell syntax only (`Copy-Item`, `Remove-Item`, `$env:NAME = "value"`; no `cp`, `rm -rf`, `export`, `&&` chains or `make`), the one-time setup below in every script, and `cd $HOME\canada-data-migration` as the first and only `cd`.

### One-time setup (copy into each script)

```powershell
# 1. Install uv (it also installs Python 3.12 for this project)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# 2. Let this window find uv without reopening it
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv --version                 # expected: a version number

# 3. Clone the repository into your home folder (needs Git for Windows: https://git-scm.com/download/win)
cd $HOME
git clone https://github.com/manuelrpmca/canada-data-migration.git
```

If the repository is already cloned, skip step 3. If it is cloned somewhere other than your home folder, replace `$HOME\canada-data-migration` in the scripts with that folder.

### Troubleshooting (errors seen on Windows)

| Error | Cause | Fix |
| --- | --- | --- |
| `-bash: cd: /home/<user>canada-data-migration: No such file or directory`, with a prompt like `[user@server ~]$` | The window is a bash terminal on another computer (for example an SSH session to a web host), not PowerShell on the Windows PC; seen 2026-11-02 | Close it and open **Windows PowerShell** from the Start menu; the prompt must start with `PS C:\` |
| `cd : Cannot find path 'C:\Users\<you>\canada-data-migration'` | The repository is not cloned in the home folder | Run step 3 of the setup, or `cd` to where it is cloned |
| `fatal: not a git repository` | PowerShell is not inside the repository folder | `cd $HOME\canada-data-migration` |
| `uv : The term 'uv' is not recognized` | uv is not installed, or was installed in this window and PATH is stale | Run steps 1 and 2 of the setup, then `uv --version` |
| The uv installer is blocked (execution policy or company policy) | PowerShell scripts are restricted | `winget install --id=astral-sh.uv -e`, then open a new PowerShell window |
| `403 Forbidden` from `www150.statcan.gc.ca` in `cdm ingest` or `cdm run` (Bank of Canada works) | Statistics Canada blocks requests from some VPN exit addresses; seen 2026-11-02 with a VPN on, gone with it off | Turn the VPN off and run `uv run cdm run` again. To check: open https://www150.statcan.gc.ca/t1/wds/rest/getCodeSets in the browser; JSON means the network is fine |
| `FileNotFoundError: ...\dbt\config\series.yml` from `uv run cdm ...` | `cdm` was run inside `dbt\`; before 2026-11-02 it only looked for `config\` in the current folder | Fixed: `cdm` now finds the repository root from any subfolder. On an older checkout, `cd $HOME\canada-data-migration` first |
| `Error: Invalid value for '--profiles-dir': Path 'C:\Users\<you>\.dbt' does not exist` | `uv run dbt ...` was run outside the `dbt\` folder, so dbt looked for its profile in the home folder | Use `uv run cdm dbt ...` from the repository folder (added 2026-11-02); it works from any folder |
| `cdm: error: argument command: invalid choice: 'dbt'` (or another new command) | The pull request that added the command is merged on GitHub but not pulled to this machine | `cd $HOME\canada-data-migration`, then `git pull`, then run the command again |
| `code 404, message File not found` for `getIcon(...)` while `cdm dbt docs serve` runs | A cosmetic request from dbt's docs page | Harmless; the docs work. Stop the server with Ctrl+C |
