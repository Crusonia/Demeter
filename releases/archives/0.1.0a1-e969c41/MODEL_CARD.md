# Demeter model card

**VALIDATION ONLY — NOT SCIENTIFIC FINDINGS.**

- Software: `0.1.0a1`; structure: `annual-health-1`.
- Source commit: `e969c41ea908ccde153f343cc66f65a7826c1884`; dirty: `False`.
- Source tree: `52e249bcbb071f65c579401c83b12d8755b3e7ea7eaff3f4d1aa1a13d3c45db6`.
- Evidence content hash: `aa0d04b884566c811caeea88430c26bcdf2c4991786245b58892b8fdc2ca9910`.
- Classification: `engineering_checkpoint`; clinical parameter fitting deferred.

## Purpose and population

An engineering health vertical: dietary exposure, metabolic transitions, mortality and period longevity. U.S. age cells 0–99 and 100+, with a closed population. Canonical snapshots use the scenarios in the profile; their full definitions and compatibility schema are in the manifest/source archive.

Baseline mortality year: 2024; population vintage: Census 2025.
All data publishers, dates, URLs, checksums, rights and reload commands are in `data-audit.json` and the source manifests.

## Calibration and validation

Clinical calibration windows and fitted clinical parameters: none. Existing annual mortality mixture normalization matches a source schedule; that arithmetic is not independent health validation. Historical benchmark training windows, interval-validation roles and holdouts are recorded per fold in `results/historical.json`.

Software/data checks passed: `True`. Scientific release ready: `false`.
Maximum population accounting residual: 5.9604645e-08 people.
The 2022→2023 mortality persistence error is -0.964478 years. This residual is retained, not tuned away; it does not validate dietary effects.

## Uncertainty, sensitivity and evidence gaps

Settings: 128 paired draws, 64 Sobol base samples, seed 42. These counts are not a convergence certificate.
Full distributions/assumptions, uncertainty summaries, Sobol indices and historical errors are archived. Synthetic parameter ranges are not empirical confidence intervals; structural/source uncertainty is incomplete.

Active baseline synthetic parameters: initial_healthy_share, initial_ir_share, initial_t2d_share, h_to_ir_rate, ir_to_h_rate, ir_to_t2d_rate, mortality_ir_ratio, mortality_t2d_ratio, beta_upf_progression, diet_lag_years, adult_age, upf_min_multiplier, upf_max_multiplier.
Registry unresolved records (including benchmarks): none explicitly marked.
Missing registry uncertainty: observed_prediabetes_65_plus.

- National age-specific metabolic transition hazards are unresolved.
- Age-specific T2D/prediabetes initial prevalence is not calibrated; CDC total diabetes includes other types.
- Dietary causal coefficient, dose scale, lag, and supported population are unresolved.
- State mortality hazard ratios remain synthetic.
- No historical end-to-end dietary-effect validation; mortality persistence backtest is a limited benchmark.

See `docs/EVIDENCE_GAPS.md`, `docs/V0_1_STATUS.md` and `docs/ISSUE_1_AUDIT.md` in the archived source for context.

## Limitations and unsupported uses

- VALIDATION ONLY — NOT A SCIENTIFIC ESTIMATE: metabolic inputs remain synthetic.
- Closed population: births and migration are zero; this is not a U.S. population forecast.
- Initial adult state fractions are constant across ages/sex; pediatric metabolic disease is omitted.
- The IR state is a synthetic prediabetes proxy; normoglycemia does not establish overall metabolic health.
- Period life expectancy freezes the current mortality schedule; it is not predicted cohort lifespan.
- Metabolically healthy years use a Sullivan prevalence weighting; this is not overall HALE.
- The 100+ tail holds state membership fixed and assumes exponential mortality within states.
- Mortality and population source uncertainty, structural uncertainty, and correlated parameters are not propagated.

No clinical recommendation, diet-induced lifespan finding, healthcare-cost forecast, agricultural result or investment conclusion is supported.

## Compatibility and changes

Scenario schema: `1`; module API: `1.0`. Only canonical baseline/intervention calculations are replayed by this bundle; experimental scenarios remain archived inputs, not validated releases.
- First reproducible bundle format; existing health equations and evidence unchanged.
- Structure version names the existing annual cohort engine, including optional experimental structures.
Declared breaking changes: none.

## Reproduction and review

Use `REPRODUCE.md`. Integrity verification checks bytes; numerical replay checks computations. Neither establishes authenticity, independent review or scientific acceptance. The generating command does not run or certify the full test suite; retain CI links and release-review decisions separately. No named scientific approval is asserted.
