# Run Demeter on your computer

Demeter currently runs as a Python program from a terminal: an app where you type
commands. It also produces an interactive HTML report you can open in a browser.
There is no server to start. You do not need an API key, a database, Docker, a paid
account, or Codex. You only need a GitHub account if you want to contribute.

You will install Git (downloads and tracks the project) and uv (installs Python
and the project's dependencies). An internet connection is needed for installation.
The included scenarios, data verification, and ordinary tests then run offline.
Run each command separately, without copying the code-block fences.

## 1. Install Git and uv

### macOS

Open **Terminal** using Spotlight. Check for Git:

```bash
git --version
```

If macOS asks to install Command Line Tools, accept and let installation finish.
If Git is still missing, run `xcode-select --install`, then reopen Terminal.
Install uv using its [official installer](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen Terminal, then check `uv --version`.
If you already use Homebrew, `brew install git uv` is an alternative.

### Linux

Open your terminal. On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install git curl
```

On Fedora, use `sudo dnf install git curl` instead. For other distributions,
install Git and curl with the distribution's package manager. Then install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen the terminal. Check `git --version` and `uv --version`.

### Windows PC

Open **PowerShell** from the Start menu. Use these commands if WinGet is available:

```powershell
winget install --id Git.Git --exact --source winget
winget install --id astral-sh.uv --exact --source winget
```

If WinGet is unavailable, install [Git for Windows](https://git-scm.com/downloads/win)
with its normal installer, then use uv's official PowerShell installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell. Check `git --version` and `uv --version`.
Use PowerShell for the Windows commands below, not Command Prompt or Git Bash.

## 2. Download and install the project

These commands work on all three platforms. They create a `Demeter` folder in
your current directory. If you already have that folder, open it with `cd Demeter`
and skip cloning; keep your own changes before updating an existing checkout.

```text
git clone https://github.com/Crusonia/Demeter.git
cd Demeter
uv sync --locked
```

The `.python-version` file selects Python 3.12. uv downloads it if needed and
creates an isolated `.venv` inside this folder; you do not need to install Python
separately or activate the environment. `--locked` uses the dependency versions
recorded in `uv.lock`. See [uv's Python guide](https://docs.astral.sh/uv/guides/install-python/).

## 3. Check it and run your first scenario

Stay in the folder containing `README.md` and `pyproject.toml`:

```text
uv run demeter validate
uv run demeter simulate scenarios/baseline.yaml --output outputs/baseline.json
uv run demeter observe scenarios/reduce_upf_30.yaml --draws 4 --samples 8 --seed 42
```

`validate` prints JSON (named fields and values). Successful software checks and
`scientific_release_ready: false` are expected together in this alpha: the
program works, but important health parameters are still synthetic. The stronger
`validate --scientific-required` check intentionally fails until evidence gaps
are closed. Do not remove that gate to make a run appear successful.

The baseline result is saved in `outputs/baseline.json`. The last command writes
`outputs/observability/index.html` and its supporting diagnostics. The small draw
and sample counts make a first run quicker; they demonstrate the tools and are
not sufficient for reliable sensitivity rankings or empirical uncertainty claims.

Open the report with the command for your operating system:

| Platform | Command |
| --- | --- |
| macOS | `open outputs/observability/index.html` |
| Linux desktop | `xdg-open outputs/observability/index.html` |
| Windows PowerShell | `Start-Process .\outputs\observability\index.html` |

You can also double-click `index.html` in your file manager. On a machine without
a desktop, copy the report to a computer with a browser. The HTML embeds its chart
library and does not need a web server or network connection.

Continue with the [first learning exercise](FIRST_EXERCISE.md).

## 4. Configure a scenario

Scenario files are plain-text YAML files in `scenarios/`. Make a copy before
editing. Use a text editor such as VS Code; keep the `.yaml` extension and use
spaces rather than tabs. Compare scenarios with the same horizon, baseline year,
and sex. The current schema supports:

| Setting | Meaning |
| --- | --- |
| `name`, `description` | Your experiment's identity and hypothesis. |
| `years` | Annual simulation horizon; the supplied examples use 25 years. |
| `baseline_year` | 2022, 2023, or 2024; defaults to 2024. |
| `sex` | `all`, `male`, or `female`; defaults to `all`. |
| `mode` | Keep `validation` for this alpha. `scientific` is evidence-gated. |
| `exposures.upf` | Relative exposure: 1.0 is baseline; 0.7 is the supplied 30% reduction exercise. It is not an absolute dietary share. |
| `exposures.fiber`, `exposures.fruit_veg` | Keep at 1.0; independent causal effects are not implemented. |

The parser rejects unsupported settings and out-of-envelope exposure changes.
Scenario choices belong in scenario files; changing an empirical assumption or
equation requires evidence review. See [the model specification](MODEL_SPEC.md).

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `git` or `uv` is not recognized | Close and reopen the terminal after installation. Recheck the relevant installation step and the installer's PATH instructions. |
| Cannot find `pyproject.toml`, evidence, or scenario | Run `cd Demeter` from the directory where you cloned it. Use `pwd` (macOS/Linux) or `Get-Location` (PowerShell) to see where you are. |
| Existing Python has dependency problems | Use the pinned environment: `uv sync --locked --python 3.12`. Do not install packages into your system Python. |
| Windows Unicode decoding error in tests | Use `uv run python -X utf8 -m pytest`. |
| Source or bundle checksum mismatch | Do not edit hashes. Fresh clones preserve exact bytes through `.gitattributes`; for an old checkout, compare with a fresh clone in another folder while preserving local work. Report any continuing failure. |
| First install cannot download packages | Check network/proxy access to GitHub, PyPI, and Python downloads. Re-run `uv sync --locked` after connectivity returns. |
| Browser report is missing | Check that `observe` completed successfully and that you are opening the report under the current checkout's `outputs` folder. |
| Charts show validation-only labels | Expected: this is an engineering prerelease, not a validated dietary forecast. See [status](V0_1_STATUS.md). |

For help, [open a setup issue](https://github.com/Crusonia/Demeter/issues/new/choose)
with your OS, command, error, and the output of `uv --version`,
`uv run python --version`, and `git rev-parse HEAD`. Remove private information.

## Update or contribute

On an unchanged checkout of `main`, run `git pull --ff-only` followed by
`uv sync --locked`. If Git reports local changes, keep those changes and follow
the [contribution guide](../CONTRIBUTING.md) instead of resetting the folder.

Contributors should also run:

```text
uv run python -X utf8 -m pytest
uv run ruff check .
uv run python scripts/verify_source_archive.py --rebuild
```

CI repeats the installation and checks on Linux, macOS, and Windows. The source
archive is already in the clone; beginners do not need to download datasets.
