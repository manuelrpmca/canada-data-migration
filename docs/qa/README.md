# QA scripts

One script per milestone, run by the owner on **Windows 11 in PowerShell** after the milestone's pull requests are merged. The commands also work in a macOS or Linux terminal unless a script says otherwise.

## Rules for every script

Anyone writing or changing a QA script follows these rules, so a script runs top to bottom on a Windows machine with no guessing:

1. **PowerShell syntax only** in code blocks (```` ```powershell ````). No bash-only commands (`cp`, `rm -rf`, `export`, `&&` chains, `source`), no `make`. Use `Copy-Item`, `Remove-Item`, `$env:NAME = "value"`.
2. **Self-contained.** A script that runs commands starts with the "One-time setup" section below, copied as is, so it works on a machine that has never run the project.
3. **Absolute starting folder.** The first command is `cd $HOME\canada-data-migration`, never a relative `cd`, so it works from any folder PowerShell opens in.
4. **One command per line,** with the expected result in a `#` comment. Comments can be pasted with the command.
5. **Quoting:** SQL passed to `cdm sql` goes in double quotes, with single quotes inside for strings.
6. **New tools** need an install line and a check line (for example `uv --version`), and the PATH line if the installer adds a folder to PATH.
7. Every new error the owner hits goes into the troubleshooting table below in the same pull request as the fix.

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
| `cd : Cannot find path 'C:\Users\<you>\canada-data-migration'` | The repository is not cloned in the home folder | Run step 3 of the setup, or `cd` to where it is cloned |
| `fatal: not a git repository` | PowerShell is not inside the repository folder | `cd $HOME\canada-data-migration` |
| `uv : The term 'uv' is not recognized` | uv is not installed, or was installed in this window and PATH is stale | Run steps 1 and 2 of the setup, then `uv --version` |
| The uv installer is blocked (execution policy or company policy) | PowerShell scripts are restricted | `winget install --id=astral-sh.uv -e`, then open a new PowerShell window |
