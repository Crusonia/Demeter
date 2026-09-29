# Mortality development benchmark for issue #1

This executes the development part of [RFC-1](rfcs/RFC-1-health-calibration.md).
It does not complete issue #1 or establish a clinical calibration. NHANES
2013–2014 was reserved and was not loaded or evaluated by the development implementation.
The subsequent [frozen evaluation](MORTALITY_VALIDATION.md) records its first outcome
intake on September 29, 2026, after a separately committed protocol; it is now used evidence.
External expert review and clinical holdout tolerances remain pending. The
approved [research-backed assessment path](SCIENTIFIC_REVIEW.md) permits further
implementation and descriptive validation under predeclared metrics. Missing
clinical evidence remains explicit. No engine parameters change.

## Reproduce

```powershell
uv run python scripts/fit_mortality_development.py
uv run python -X utf8 -m pytest tests/test_mortality_development.py
```

The command reads only the pinned 2011–2012 public files already in the repository
store and writes aggregate results to `outputs/mortality-development.json`.
The [saved receipt](validation/issue-1-mortality-development.json) retains the
source, implementation and evidence hashes, complete specification, coefficients,
joint covariance, intervals, exclusions, numerical diagnostics and subgroup
residuals. Floating-point estimates are reconstructed within explicit test
tolerances across platforms; raw source integrity remains byte-exact.

## Population and estimand

The likelihood describes time from examination to death or administrative
censoring, conditional on baseline age, sex and glycemic observation. The full
model includes prediabetes and any-type diabetes indicators; the comparison
includes age and sex only. Both versions are also fitted with a continuous
attained-age log-hazard slope change at the registered age-60 knot. The original
fits are retained. Reference is a female participant at the registered
adult minimum age, in the normoglycemic category. The age coefficient acts on
attained age continuously through follow-up. Coefficient units and numerical
controls are registered in `evidence/parameters.yaml`.

Among 2,842 positive fasting-weight records, sequential exclusions are 527 below
the adult minimum, 21 known pregnancies, 7 missing glycemic observations, 3
linkage-ineligible records and 109 with top-coded age. No additional record was
excluded for unknown sex or missing/zero follow-up. The development domain has
2,175 records and 161 observed deaths. These are sample counts, not population
rates. Age-group names in the receipt inherit the survey definitions but are
restricted to the selected domain: its oldest group ends below age 80.

Original fasting weights are used without a new selection adjustment.
[CDC's linked-file guidance](https://www.cdc.gov/nchs/data/datalinkage/public-use-linked-mortality-file-description.pdf)
notes uncertainty in the properties of original weights under incomplete linkage.
Complete-case and linkage selection remain limitations, not resolved merely by
small exclusion counts. Public follow-up perturbation also remains relevant.

## Executed result and interpretation

All four proposed models converged with finite survey covariance, using 17 design
degrees of freedom. The glycemic model has higher in-sample weighted likelihood,
which is expected to be possible when adding covariates and is not evidence of
out-of-sample improvement. Its prediabetes log-hazard interval includes zero;
this does not prove an absent causal effect. The receipt retains all estimates
and the age/sex/category residuals without selecting favorable cells.

The aggregate observed/integrated-event-intensity ratio is approximately one
for all models because of the fitted intercept score equation. It must not be
reported as a successful mortality validation. Event probabilities evaluated at
event-dependent follow-up times are not substituted for this counting-process
diagnostic. Sparse subgroup residuals receive no invented pass thresholds.

Numerical checks cover independent adaptive quadrature, zero and negative age
slopes, finite-difference score/Hessian comparisons, weight-scale invariance,
empty-domain PSU variance, missing outcomes, zero follow-up, absent deaths,
unidentified designs, iteration failure and offline reconstruction. These
checks validate arithmetic and data handling, not clinical transport.

## Evidence change and remaining requirements

Eighteen coefficients (eight original and ten alternative-age coefficients) have estimated, grade C,
benchmark-only values and survey t intervals in the registry. The coefficients
share the saved covariance and must not be sampled independently. No priors,
causal effects, clinical bounds, or current-state mortality ratios are inferred.
The matching null fit for each age form is preserved as a comparator. The engine's synthetic ratios and
all existing scenario assumptions remain unchanged.

The [before/after receipt](validation/issue-1-mortality-development-before-after.json)
compares baseline and UPF-reduction scenarios against commit `a1b638d` with
identical settings. Only the evidence provenance hashes differ; all numerical
outputs are identical. No new coefficient enters Monte Carlo or sensitivity
draws. This software-equivalence check is separate from scientific validation.

Source bytes and reuse terms remain those of the
[linked-mortality archive](LINKED_MORTALITY.md). This public baseline-category
model has no repeated glycemic observations and cannot identify progression,
reversal, diet response or state changes before death. National initialization,
T2D classification, current-state hazards, dietary dose/lag and independent
forward health validation still require evidence. Scientific review is pending;
the full issue #1 release gate remains closed.
