# QA scripts

One script per milestone, run by the owner on **Windows 11 in PowerShell** after the milestone's pull requests are merged. The commands also work in a macOS or Linux terminal unless a script says otherwise.

## Rules for every script

Anyone writing or changing a QA script follows these rules, so a script runs top to bottom on a Windows machine with no guessing:

1. **PowerShell syntax only** in code blocks (```` ```powershell ````). No bash-only commands (`cp`, `rm -rf`, `export`, `&&` chains, `source`), no `make`. Use `Copy-Item`, `Remove-Item`, `$env:NAME = "value"`.
2. **Self-contained.** A script that runs commands starts with the "One-time setup" section below, copied as is, so it works on a machine that has never run the project.
3. **One folder for the whole script.** The first command is `cd $HOME\canada-data-migration`, and no later command changes folder. dbt runs through `uv run cdm dbt <command>`, never `cd dbt` + `uv run dbt`.
4. **One command per line,** with the expected result in a `#` comment. Comments can be pasted with the command.
5. **Quoting:** SQL passed to `cdm sql` goes in double quotes, with single quotes inside for strings.
6. **New tools** need an install line and a check line (for example `uv --version`), and the PATH line if the installer adds a folder to PATH.
7. **Restart from the top after any merge.** If a pull request is merged while you are running a script, start again from its first line: `git pull` brings the change to your machine, and a command added by that change does not exist until then.
8. Every new error the owner hits goes into the troubleshooting table below in the same pull request as the fix.

## One-time setup (copy into each script)

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

## Troubleshooting (errors seen on Windows)

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
