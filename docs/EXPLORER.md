# Learn and experiment in Demeter Explorer

Explorer is an optional local learning interface for the existing Python model.
It pairs charts with explanations and lets you save and rerun assumptions. It is
a validation-only preview: the health engine still contains synthetic effects.
It does not establish dietary benefits, treatment recommendations, healthcare
savings, or investment value.

## Start on macOS, Linux, or Windows

First follow [Getting started](GETTING_STARTED.md) to install Git and uv and clone
the repository. For the interface, also install **Node.js 24**, which includes npm,
from the [official Node.js download page](https://nodejs.org/en/download). Choose
version 24 and your operating system. On Linux, follow that page's installation
instructions for your distribution. Close and reopen your terminal after installing.

From the Demeter folder, these commands work on all three platforms:

```text
node --version
npm --version
uv run --extra studio demeter explore
```

The first command should report `v24.x`. The first launch downloads the optional
Python dependencies and builds the interface using the committed npm lockfile.
An internet connection is needed for that installation. It can take a few minutes.
Later launches reuse the build unless the frontend source changes.

The launcher starts one Python service on your computer and opens your browser.
There is **no separate Next.js server** to start. Next.js generates static browser
assets; Python serves those assets and runs the model. Keep the terminal open.
Press **Ctrl+C** there when finished. Calculations and saved files stay local.

If the browser does not open, copy the full local link printed in the terminal,
including its `#token=…` fragment. The launch token connects that browser session
to the local API; it is removed from the address bar after opening. Each launch
gets a new token. No account, API key, database, Docker, or paid service is needed.

Optional flags:

```text
uv run --extra studio demeter explore --no-browser --port 8765
uv run --extra studio demeter explore --destination outputs/my-experiments
```

The default port is chosen automatically. Runs live under `outputs/explorer/`,
which Git ignores. A second Explorer cannot write into the same run directory.
After installation, calculations, charts and exports work without internet access.
External source links naturally need a connection.

## A first learning exercise

1. Read **Learn**. Start with “Follow the people”: stocks count people; flows move
   people between states. Births and migration are zero in the current model.
2. Open **Experiment**. Choose the core UPF reduction example. Record a prediction
   before running it: which curve should move first, and why?
3. Click **Run experiment**. A preview uses four uncertainty draws and eight Sobol
   base samples. These small counts demonstrate the analysis pipeline; they do not
   support reliable rankings or empirical confidence claims.
4. In **Explore**, inspect the chart, its adjacent explanation, **Data**, and
   **Sources**. Change the chart selector to see stocks, flows, dependencies,
   life tables, uncertainty, sensitivity, or historical benchmarks.
5. Read the comparison with the frozen no-intervention reference. It uses the same
   population selection, horizon and health structure and the original registry.
   Stocks and flows can also show dotted reference lines.
6. Change one assumption in **Experiment**, predict its effect, and run again.
   Select a completed run as the reference if you want to compare two experiments.
   The assumptions diff shows exactly what changed. Saved results never update
   just because you edited the form.
7. Add a reflection to the result and save the note. Reopen it from **Saved runs**.
   Export a chart CSV/JSON/PNG, scenario YAML, evidence snapshot, comparison JSON,
   diagnostics, or a self-contained offline HTML report.

The report and interface use the same reviewed chart commentary. Summary sentences
describe the actual run and its full time range. A change within one run is distinct
from a difference between two runs. Period life expectancy is a mortality-schedule
measure, not a prediction of an individual's lifespan.

## What the controls mean

The reviewed project catalog supplies baseline health, PreChronic, dietary timing,
and GLP-1 examples. These run the canonical Python engine; the browser does not
implement a second set of equations. The catalog does not execute arbitrary
community Python extensions from a browser request.

- **Simple controls:** scenario, horizon, population sex, mortality vintage, health
  structure, UPF exposure/schedule, dietary response shape, and GLP-1 access schedule
  when that model is selected. Absolute food fields retain their units and reference
  period. Context-only fiber and fruit/vegetable fields do not activate new effects.
- **Advanced controls:** active synthetic parameters and existing uniform sampling
  ranges. Nominal values must fit their ranges. Observed, estimated and derived
  evidence is read-only. Switching structure or response type/shape clears advanced
  overrides because the applicable parameter set can change.
- **Preview / standard:** four / 64 uncertainty draws and eight / 32 Sobol base
  samples. Both are learning profiles; inspect convergence before interpreting a
  ranking. The seed is saved. Changing a nominal value alone keeps the original
  sampling distribution; edit both bounds explicitly to change a uniform range.
- **Reference:** a no-intervention run using original evidence, or a compatible
  completed run. Saved references require the same base evidence registry, engine
  source and bundled-data fingerprint,
  horizon, vintage, sex, mode and health structure. Comparisons show absolute and
  relative nominal changes. Independent uncertainty bands are never subtracted
  to manufacture an interval for the difference.

Only one calculation runs at a time. You can cancel it; failed, cancelled and
interrupted jobs remain visible and are never presented as completed results.
Closing the service cancels active work. Large GLP-1 or standard-profile runs take
longer because they include canonical uncertainty and sensitivity calculations.

Agriculture, regenerative practices, retail value capture and healthcare economics
appear as **Planned**, with links to design documents. They are research directions,
not working model controls. See [the staged roadmap](PROJECT_VISION.md).

## Reproducibility and development

Each run directory freezes its request, resolved evidence, scenario, computation
settings, reference results, teaching content, source fingerprint and provenance.
The source evidence registry and repository datasets are never overwritten by
form edits. Subsequent notes are stored separately from the original request.
Keep the complete run directory and corresponding source checkout for reproducible
work; exports are not a replacement for the [release archive](RELEASES.md).

`src/demeter/explorer/` is the optional HTTP/job adapter. `web/` is the static Next.js
frontend. Reviewed commentary lives in
[`src/demeter/analysis/content/charts.md`](../src/demeter/analysis/content/charts.md).
The core library and existing CLI/report commands work without the `studio` extra
or Node. This interface adds no model equations and does not relax the scientific
release gate.

Contributor checks:

```text
uv sync --locked --extra studio
npm ci --prefix web
npm run check --prefix web
npm test --prefix web
uv run python scripts/build_explorer.py
uv run --extra studio python -X utf8 -m pytest
uv run ruff check .
uv run playwright install chromium
uv run --extra studio python scripts/verify_explorer_browser.py
```

The launcher rebuilds stale frontend assets automatically. Python code changes
require restarting it. Generated assets live in the ignored `build/explorer/`
directory, outside the scientific source tree; wheels include them as package assets.
`npm run dev --prefix web` is available for frontend work,
but it is not the normal launcher and does not supply a model API by itself.
Package builds include compiled assets; building a wheel/sdist from source requires
Node 24. An installed wheel can serve its bundled assets without Node, but still
needs a Demeter checkout (`--project PATH`) for the reviewed scenarios and evidence.

Troubleshooting: if Node or npm is missing, install Node 24 and reopen the terminal;
if a port is occupied, omit `--port`; if the session cannot connect, reopen the
current launcher's complete link; if a run fails, read its visible error and
`outputs/explorer/<run-id>/error.log`. Do not change scientific mode or source data
to suppress a validation error.
