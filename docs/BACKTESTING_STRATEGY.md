# Demeter — Historical Reconstruction and Backtesting Strategy

## Purpose

Demeter must be tested against history, not only calibrated to the present.

A credible system-dynamics model should reproduce important historical trajectories and predict held-out periods using parameters and causal structure established before those periods.

The objective is not to maximize fit. The objective is to discover where the model's causal structure is incomplete, unstable, or overfit.

## Historical horizon

Demeter should aim to reconstruct multiple recent decades of U.S. food, metabolic-health, chronic-disease, mortality, and healthcare dynamics.

A practical initial target is approximately 1970 to the present, with the actual start date for each variable determined by data comparability.

Do not create false continuity where definitions or measurement methods changed.

## Candidate authoritative data sources

### Mortality and life expectancy

- CDC / NCHS U.S. Life Tables
- National Vital Statistics System mortality data

Use annual or decennial life tables as available and preserve vintage/methodology metadata.

### Population health and metabolic state

- NHANES I: 1971–1975
- NHANES II: 1976–1980
- NHANES III: 1988–1994
- Continuous NHANES: 1999 onward
- historical NHES when useful for earlier health-state context
- NHIS / CDC diabetes surveillance for diagnosed disease trends

The model must account for survey redesign, laboratory-method changes, diagnostic-definition changes, and gaps between survey eras.

### Food and nutrient environment

- USDA ERS Food Availability (Per Capita) Data System
- USDA ERS Loss-Adjusted Food Availability data
- historical USDA nutrient-availability series

National food-availability series are proxies for consumption, not individual dietary intake. Treat them accordingly.

### Population and economics

- U.S. Census population estimates
- BLS inflation / price indexes where needed
- USDA price and commodity series where needed

### Healthcare economics

When provider economics is implemented, candidate sources include:

- CMS National Health Expenditure data
- CMS hospital cost-report datasets
- Medicare utilization / payment datasets
- AHRQ HCUP where licensing/access and methodology permit
- hospital financial filings / cost reports where appropriate

## Backtest modes

### 1. Structural baseline reproduction

Before any held-out forecast, Demeter should reproduce basic historical quantities:

- population by age cohort
- mortality schedule
- life expectancy
- diagnosed diabetes prevalence/incidence
- selected metabolic-risk distributions
- selected diet/food-availability trajectories

This is necessary but not sufficient.

### 2. Rolling-origin forecast

Use repeated pseudo-forecast experiments:

```text
fit / calibrate using data available through year T
        ↓
freeze parameters that would have been known at T
        ↓
forecast T+5 and T+10
        ↓
compare with observed data
        ↓
advance T and repeat
```

This exposes parameter instability and structural drift.

### 3. Era holdout

Where measurement comparability allows, define distinct historical eras.

Candidate framing:

- 1970s / early 1980s
- late 1980s / 1990s
- 2000s
- 2010s
- 2020 onward as a distinct structural-break period

Exact boundaries should be driven by data definitions, not convenience.

### 4. Shock tests

Explicitly test the model around major exogenous changes.

Examples may include:

- smoking decline
- antihypertensive treatment changes
- statin adoption
- diagnostic threshold changes
- recessions and food-price shocks
- demographic aging
- COVID-era mortality disruption
- recent GLP-1 adoption

Demeter should not force food-system variables to explain changes caused by omitted exogenous factors.

## Calibration versus validation

Maintain a machine-readable distinction between:

- calibration targets
- validation targets
- holdout targets
- exogenous inputs

A dataset or time window used to tune a parameter cannot simultaneously count as independent validation for that parameter.

## Metrics

At minimum compute:

- mean absolute error
- mean absolute percentage error where denominator behavior permits
- root mean squared error for trajectories where useful
- age/cohort-specific residuals
- bias over time
- uncertainty interval coverage
- calibration-to-holdout degradation
- sensitivity drift
- parameter drift

Do not choose metrics mechanically; use metrics that match the modeled quantity and decision question.

## Visual diagnostics

Backtesting should automatically produce:

- observed vs predicted trajectories
- residual plots
- cohort heat maps
- uncertainty bands
- calibration-window / holdout-window overlays
- parameter drift charts
- sensitivity-rank changes over time

These views are part of model validation, not optional presentation polish.

## Versioned historical runs

Every historical reconstruction should record:

- model version / commit
- evidence-registry hash
- data vintages
- calibration window
- holdout window
- scenario/exogenous assumptions
- random seed where relevant

Historical results should be reproducible.

## Acceptance gate for new modules

A new major module should not be called validated merely because it improves current-period fit.

Before an upstream module becomes part of the trusted integrated model, it should demonstrate at least one of:

1. improved held-out historical prediction
2. improved reproduction of an independently measured intermediate variable
3. a clearly evidenced mechanism that resolves a known structural failure

If it only adds degrees of freedom and improves in-sample fit, treat it as unvalidated.

## Special treatment of recent structural changes

Recent periods involving COVID-era mortality and rapid GLP-1 adoption should be treated as explicit regime changes.

Do not assume parameters calibrated before those shocks remain stationary.

The model should distinguish:

- structural parameter change
- exogenous shock
- temporary disturbance
- measurement change

## Long-term goal

Eventually Demeter should be able to answer:

> If we had frozen the model and evidence base at a past date, how well would it have predicted what happened next?

That is a much stronger credibility test than matching today's observed values.
