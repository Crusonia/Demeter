# Scientific model observability

Issue #7 adds **model instrumentation**, not a public simulator. Charts describe
what the implemented model does and expose what it cannot support. Every report
keeps the validation-only warning and the distinction between sourced historical
observations and synthetic model mechanisms.

## Reproduce and inspect

```bash
uv sync --locked
uv run demeter observe scenarios/reduce_upf_30.yaml \
  --draws 64 --samples 32 --seed 42 --destination outputs/observability
# Open outputs/observability/index.html locally; no network service is required.
uv run demeter visualize outputs/observability/diagnostics.json \
  --destination outputs/observability-rendered
uv run pytest tests/test_observability.py
```

`observe` runs canonical model/analysis functions once. It writes their complete
JSON, 34 Plotly figure JSON files and a self-contained HTML report with Plotly.js
embedded. `visualize` reads that saved JSON and performs no model run, evidence
lookup, sampling or equation evaluation. Rendering the same data is deterministic.
The report is responsive and supports Plotly hover, pan, zoom and trace selection.
The notebook `notebooks/observability.ipynb` reads the same saved file and calls
the same figure builder; select the project environment as its Jupyter kernel.
Jupyter is an optional authoring environment, not a model runtime dependency.

## Views and canonical inputs

| View | Input / interpretation |
| --- | --- |
| Living stocks and annual flows | Engine `annual` counts and emitted flow totals; year 0 is an initial snapshot |
| State transitions / stock-flow graph | Engine-exported transition specification including explicit death flows |
| Dependency graph | Engine-exported implemented dependencies; an arrow does not establish causality |
| Age-cell trajectories | Instrumented annual 101-age × 3-state stocks; 100+ pools ages |
| Mortality and period life-table curves | The exact tables calculated by `period_outcomes`; annual 100+ death probability distinguished from terminal interval q=1 |
| Uncertainty bands | Annual quantiles of the actual canonical Monte Carlo runs, with no resampling in the renderer |
| Sobol rankings | Canonical total-order indices and reported confidence half-widths; no clipping of noisy estimates |
| Parameter distributions | Histograms of actual sampled parameter values, with registered units/status/grade |
| Historical observations, predictions, intervals and residuals | Canonical #6 per-fold outputs, separated by definition segment; no independent forecast code |
| Evidence overlays | Registry records exported by the engine; synthetic graph edges are dashed amber, source/grade visible on hover |

The engine's `simulate(..., diagnostics=True)` option captures diagnostics without
changing dynamics. The default library path avoids retaining large histories.
`uncertainty(..., diagnostics=True)` records sampled values and annual intervals
without changing random draws, outcome summaries or paired deltas. Recording a
full sampled cohort history for every draw is deliberately unnecessary.

Age-cell heatmaps are not identified birth-cohort survival curves, especially in
the pooled 100+ cell. No PreChronic state is drawn before it is implemented.
The IR/prediabetes proxy and current mortality decomposition remain synthetic.
The dependency graph describes this implementation, not every potential causal
factor or the entire future project architecture. An absent effect is not evidence
that the real-world effect is zero.

## Historical interpretation

The report displays each source's units, forecast origins in hover text, structural
break annotations, and achieved coverage/error tables. Different measurement
segments are not connected by observed lines. Missing interval bounds remain
missing. Intervals are empirical pre-origin benchmark bands; the nominal coverage
is not guaranteed. The full JSON contains calibration/holdout roles, fitted
parameters, source receipts and skipped-fold reasons.

Historical forecasts still do not validate the integrated health model or identify
dietary causal effects. See `HISTORICAL_BACKTESTS.md` for exact limitations and the
remaining #6 scientific criteria. Sensitivity is variance under registered
synthetic ranges and is separate from evidence strength; it is not an intervention
ranking or policy recommendation. Global causal attribution remains issue #26.

## Verification

Tests compare instrumented and uninstrumented results exactly, check stock/flow
conservation and the terminal mortality distinction, verify annual interval
endpoints against the canonical outcome summaries, inspect trace values against
saved outputs, and confirm rendering neither imports engine equations nor mutates
payloads. CLI re-rendering and embedded/offline Plotly export are tested. The
full repository suite and CI also generate a small report from canonical data.

Headless Chromium verification blocks HTTP/HTTPS and requires all 34 Plotly charts
to initialize without JavaScript errors. Desktop/mobile screenshots and graph /
historical-panel rendering were inspected during implementation. This browser
check also runs in Python 3.12 CI. Notebook cells are executed directly in tests;
a separate Jupyter kernel could not start in the build workspace because its
socket operation was denied, so that interactive kernel launch is not claimed
as verified. The same cells execute without a kernel process.
