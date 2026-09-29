# Reserved-cycle mortality prediction assessment

All four frozen development models have now been evaluated on NHANES 2013–2014
with public mortality follow-up through 2019. Their aggregate glycemic-versus-null
score contrasts are small and their pointwise intervals span zero. This is an
executed descriptive temporal prediction check, not demonstrated clinical
adequacy, a dietary effect, or validation of current-state mortality hazards.
No model was refitted, recalibrated, selected or promoted into the engine.

Issue: [#55](https://github.com/Crusonia/Demeter/issues/55), supporting #1 and #27.
Method: [RFC-55](rfcs/RFC-55-mortality-holdout.md).
Author: Codex-assisted analysis for the Food is Health-affiliated project,
September 29, 2026 (UTC). External expert review and maintainer disposition
remain pending; no independent human review is claimed.

## Chronology and reproducibility

- Protocol, all eighteen existing coefficients, joint covariance, evaluator and
  pre-outcome tests were committed at
  [`f1cab86`](https://github.com/Crusonia/Demeter/commit/f1cab860b13cb7089b7adf3a73bdc98bcfbbf605)
  at 01:54:44 UTC. All 438 Python tests and Ruff passed before this commit.
- [Draft PR #60](https://github.com/Crusonia/Demeter/pull/60) was opened at
  01:54:48 UTC, before the first intake. The original draft description explicitly
  recorded that reserved outcomes had not been inspected.
- The five original public-use files were retrieved at 01:55:02–01:55:06 UTC;
  the mortality file receipt is 01:55:06 UTC. Original bytes, URLs, source
  documentation, terms and exact times remain in the
  [source manifest](../data/sources/nhanes-mortality/2013-2014/manifest.json).
- This assessment follows that intake. Source definitions, coefficients, protocol
  and metrics are unchanged; the later interpreter guard correction is disclosed
  below. The reserved cycle is now
  **used evidence**; later model revisions cannot call it untouched validation.

The [protocol snapshot](validation/mortality-validation-protocol-v1.json) has
SHA-256 `440c44a18a743e6c9d1cc345aabbaf7631033fdb640d9062bba6a748c0abb091`.
Its original RFC describes the pre-outcome stage and remains unchanged as part
of that snapshot. The [original aggregate receipt](validation/issue-55-mortality-validation.json)
records every prespecified domain and comparison, source/code hashes, the
freeze commit and the exact evidence-registry hash used for this evaluation.
Only aggregate analysis results are exported; public files are joined in memory.

### Post-intake implementation amendment

The [automated review](https://github.com/Crusonia/Demeter/pull/60#discussion_r4128954589)
found that a manifest from another protocol was rejected only after its data had
been parsed. The corrected reader rejects a missing or mismatched protocol hash
before opening any outcome or baseline source. Regression tests prohibit parser
calls and omit the data files entirely to verify this ordering.

Outcomes had already been inspected when this correction was made. The
[pinned amendment](validation/mortality-validation-implementation-amendment-1.json)
retains the original and amended interpreter hashes, original freeze/result
commits, review link and explicit post-intake disposition. The original protocol,
RFC, source archive and first result are unchanged; no scientific choice is
re-registered. Only this documented interpreter override is allowed; every other
protected file and all coefficient/definition contracts remain checked.

The [amended receipt](validation/issue-55-mortality-validation-amended.json)
is the current offline command's output. Its provenance distinguishes the original
protected implementation from the actual executed implementation and includes the
amendment hash. Every non-provenance result is exactly identical to the original
receipt. This is a software guard correction, not a new independent data test.

From a source checkout on macOS, Linux or Windows:

```text
uv sync --locked --extra studio
uv run python scripts/validate_mortality_holdout.py
uv run demeter data verify-store
uv run demeter data verify-packages --check-tracked
uv run python -X utf8 -m pytest tests/test_mortality_validation.py
```

The evaluator writes `outputs/mortality-validation.json` offline. Do not use
`--download` with the existing archive; that flag is only for the first intake
and refuses an already completed store. Runtime checks reject drift in the
frozen implementation, definitions or coefficients before reading outcomes.
The test compares all saved numerical diagnostics with relative tolerance
`1e-10` and absolute tolerance `1e-12` for platform arithmetic, not clinical
acceptance. Source and protocol checksums remain byte-exact.

## Population, coverage and exclusions

Of 10,175 demographic source records, 2,927 have positive fasting weights. In
the frozen sequential exclusion order, 537 are below the adult minimum, 20 have
known pregnancy, 2 lack complete glycemic observations, 2 are linkage-ineligible,
152 have top-coded age, none lack sex, and 1 lacks positive examination follow-up.
The analysis has **2,213 participants and 93 observed deaths**, with baseline
ages 20–79. The public survey's `20_plus` and `60_plus` labels in the receipt
are restricted to that eligible age range, not all older adults.

The baseline groups contain 942 normoglycemic participants / 23 deaths,
921 with prediabetes / 38 deaths, and 350 with any-type diabetes / 32 deaths.
These are unweighted sample counts, not national rates. Actual examination
follow-up ranges from 5 to 85 months; its survey-weighted mean is about 5.892
years. Original fasting weights are retained without a new linkage or item-
nonresponse correction. Missing linkage never means survival.

Each model has 37 reported domains: the overall eligible sample and registered
age × sex × baseline-category cells. These overlap and must not be summed.
Five cells have no observed deaths and explicitly unavailable ratio intervals.
Sparse cells remain visible and are not evidence of safety or equivalence.
The overall domain represents 30 PSUs across 15 strata; domain support and
degrees of freedom accompany each cell.

## Results under the prespecified method

The ratio is weighted observed events divided by integrated event intensity over
each participant's observed at-risk time. It is not a common-horizon death
probability. The absolute weighted totals are retained in the receipt; they must
not be presented as a national forecast of deaths. Intervals below are 95%
pointwise survey intervals conditional on the frozen fitted predictors.

| Frozen predictor | Observed / integrated intensity | Interval |
| --- | ---: | --- |
| Single-slope age, with glycemic categories | 0.913 | 0.697–1.194 |
| Single-slope age, age/sex only | 0.942 | 0.736–1.205 |
| Piecewise age, with glycemic categories | 0.934 | 0.718–1.216 |
| Piecewise age, age/sex only | 0.961 | 0.757–1.220 |

All point estimates are below one; expected integrated intensity exceeds observed
events in this sample. All intervals include one. That does not establish
acceptable calibration, because no defensible clinical tolerance was declared.

Higher paired censored log score favors the left-hand predictor descriptively:

| Prespecified comparison | Mean score difference | Interval |
| --- | ---: | --- |
| Glycemic minus age/sex-only, single slope | 0.000854 | -0.004458–0.006167 |
| Glycemic minus age/sex-only, piecewise | 0.000990 | -0.004702–0.006681 |
| Piecewise minus single slope, glycemic | -0.000068 | -0.002440–0.002305 |
| Piecewise minus single slope, age/sex only | -0.000203 | -0.002357–0.001951 |

These comparisons do not demonstrate a predictive advantage for the added
glycemic terms or the piecewise age form. They also do not establish absence
of an effect. No superiority test, multiplicity-adjusted finding, clinical pass
or winning specification is asserted. All subgroup comparisons remain in the
receipt, including unfavorable and imprecise results.

## Scope and unresolved objections

This checks transport of four specific fitted baseline-category predictors to
another survey cycle. It does not observe later metabolic state changes or
identify the mortality effect of changing a person's state. All-type diabetes
is not T2D; normoglycemia is not overall metabolic health. Pediatric and oldest-
age hazards, dietary causality and national initialization remain unresolved.

[CDC's public linked-file documentation](https://www.cdc.gov/nchs/data/datalinkage/public-use-linked-mortality-file-description.pdf)
describes perturbation of some follow-up times and unperturbed vital status.
Original-weight properties under incomplete linkage, complete-case selection and
different follow-up duration remain limitations. The
[2013–2014 glucose documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/GLU_H.htm)
also describes a laboratory/method change from the development cycle. No
outcome-selected correction was applied.

Intervals estimate validation-sample uncertainty conditional on the frozen
predictor. They exclude uncertainty in the development fit, unmeasured
confounding, measurement, model selection and transport. The joint development
covariance is preserved for provenance, not independently resampled. Future
total-uncertainty claims require a different explicit estimand and protocol.

The [before/after engine receipt](validation/issue-55-mortality-validation-before-after.json)
compares the baseline and UPF-reduction scenarios with the registry at `031a59e`.
Only registry provenance hashes differ; all numerical outputs are identical.
Active parameters remain synthetic. The new dataset is derived, grade C,
prediction-benchmark-only, and does not enter Monte Carlo or sensitivity draws.
Source reuse is recorded in the [rights inventory](../data/rights.json).

Software verification, this scoped predictive assessment, external expert review,
maintainer merge and scientific release remain distinct. Issue #55's evaluation
is implemented; #1 and the health gates remain open. The next evidence work is
[observation mapping, longitudinal hazards and a specified dietary pathway](NEXT_STEPS.md).
