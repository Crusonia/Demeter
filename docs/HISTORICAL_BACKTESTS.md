# Historical benchmarks and holdout contract

Issue #6 now has an executable offline historical validation harness. These are
**univariate historical forecast benchmarks, not validation of the integrated
food-to-health model**. They establish observable targets and falsifiable error
reports without fitting a dietary coefficient to omitted causes.

## Data contract

Thirteen series are pinned in `src/demeter/data/bundled/historical.json`:

| Source | Observations | Definition and limitations |
| --- | --- | --- |
| CDC/NCHS NVSS `w9j2-ggv5`, September 2020 revision | 1970–2018 life expectancy and age-adjusted mortality, all races, both sexes/male/female | Published rounded aggregates; not age-specific mortality schedules. Metadata still says 2017, while the all-race source rows include 2018. |
| CDC USDSS `c9xs-vhst`, June 2026 revision | 2000–2024 diagnosed diabetes, four age groups, crude and age-adjusted adults | NHIS self-report, civilian noninstitutionalized adults, excludes gestational-only diagnoses; all diabetes types, not total T2D. Published observation confidence limits retained. |
| USDA ERS added sugar/sweetener availability, September 2024 vintage | 1970–2023 total caloric sweeteners | Pounds dry weight/person/year, supply/disappearance before losses; not personal intake, sugar-sweetened beverages, or UPF. |

The historical manifest records retrieval timestamps, source URLs including the
exact NHIS query, vintages, licenses, transformations and raw/bundle SHA-256 hashes.
The evidence registry references the manifest. Raw downloads remain immutable in
`data/raw/historical`; changed checksums fail before rewriting derived data.
Bundled derived observations make normal execution independent of network access.

Primary documentation:
- [NCHS source](https://data.cdc.gov/d/w9j2-ggv5)
- [NHIS definitions, weighting and 2019 redesign](https://usdss.cdc.gov/diabetes/data/socrata/National_Burden_Magnitude_methods.html)
- [USDA definitions](https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system/food-availability-documentation)

## Forecast and uncertainty contract

At each origin T, persistence and ordinary least-squares linear trend use only the
last 10 consecutive, comparable annual observations ending at T. They predict
T+5 and T+10; a selected `--origin` freezes one origin. `--window` changes the
training length explicitly, never by optimizing holdout performance. Regression
level and slope are diagnostic estimates in the run, not clinical parameters.

A forecast interval uses absolute errors of earlier same-method, same-window,
same-horizon forecasts whose **target** year is at or before T. Its radius is the
order statistic `ceil((n+1)*coverage)` (default coverage 0.90). If there are too few
errors, both limits and coverage are null, not zero. Serial dependence and regime
changes invalidate an exchangeability guarantee; these are empirical diagnostic
bands whose achieved coverage must be inspected. No observation confidence
interval is relabeled as a predictive interval. Intervals are not clipped to
physical bounds; they describe benchmark uncertainty, not bounded health states.

Each fold records calibration years, earlier interval-validation target years,
holdout year, observations, predictions, signed residual (observed minus
predicted), interval limits, fitted coefficients and calibration RMSE. Earlier
validation observations can later enter a rolling calibration window; they are
not independent validation of that later fit. Its outer holdout remains excluded.
No model-selection tuning occurs. All series/method/horizon/definition groups
report N, MAE, RMSE, bias, MAPE (null with any zero denominator), interval N and
coverage, plus holdout-minus-calibration RMSE. Units are never pooled across series.

## Structural breaks and omitted causes

NHIS forecasts cannot cross the 2019 redesign. Mortality-rate folds conservatively
separate pre-1999 historical rates from the explicit 2000-standard series. Gaps
are not interpolated or crossed. Skipped folds retain their reasons. With the
default 10-year window the comparable 2000–2018 NHIS segment has 5-year forecasts
but insufficient history for a 10-year forecast; `--window 5` permits the latter.
Post-redesign NHIS remains too short for default long-horizon evaluation.

The run carries COVID (2020–2022 diagnostic window) and post-2021 obesity GLP-1
regime annotations and names smoking, medications, diagnostic changes, demographic
aging and non-food mortality as unmodeled causes. Shock dates are annotation
choices, not assertions that a shock stopped or that earlier GLP-1 treatment did
not exist. No shock effect size is invented or fitted after the origin. No
benchmark consumes food as a mortality/diabetes covariate. Thus residuals cannot
be assigned to food by construction. Full exogenous adjustment remains necessary
before interpreting a future causal integrated-model backtest.

## Reproduce

```bash
uv sync --locked
uv run demeter data rebuild-history --download
uv run demeter historical-backtest --output outputs/historical-backtest.json
uv run demeter historical-backtest --origin 2000 --output outputs/era-2000.json
uv run demeter historical-backtest --window 5 --output outputs/history-window-5.json
uv run pytest tests/test_historical.py
```

Runs record the package version, commit and dirty flag (when running from a git
checkout), digest of Python source, evidence hash, data/manifest hashes, all
windows, nominal coverage, and a null seed because the algorithms are deterministic.
Installed wheels can have a null commit; source/data/evidence digests still identify
the computation. A compact validation receipt is committed in
`docs/validation/issue-6-historical-summary.json`; full per-fold artifacts are
regenerated by the CLI. Plotting consumes these outputs in issue #7.

## Acceptance and remaining work

Implemented: multi-decade mortality/diabetes/food observations, explicit temporal
roles, 5/10-year rolling origins, fixed-origin diagnostics, incompatible-definition
exclusions, residual/error/coverage diagnostics, deterministic offline execution
and run/source receipts. Leakage, gaps, source drift and arithmetic are tested.

Still unresolved: age-specific historical cohort reconstruction, NHANES metabolic
risk distributions, historical exogenous-factor magnitudes and the **integrated
health model's** independent holdout performance/parameter/sensitivity drift.
Present-day synthetic state parameters cannot be claimed validated by these
benchmarks. Issue #6 remains open for those integrated scientific criteria; this
completed harness is independently usable by #7 and later model work. Neither
#1 nor milestone #27 is marked complete.
