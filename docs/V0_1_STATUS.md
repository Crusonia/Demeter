# v0.1 acceptance status

Release identifier: **0.1.0a1**. Engineering functionality is implemented; scientific release gates remain open.

| Acceptance criterion | Status | Evidence |
| --- | --- | --- |
| Explicit U.S. age cohorts; support sex strata | Implemented | Census counts at ages 0–99, 100+; all/male/female source schedules |
| Healthy, IR/prediabetes, T2D states | Implemented with synthetic allocation | Three stocks; definitions and prevalence not calibrated |
| Optional PreChronic structure | Engineering implemented; scientific mapping unresolved | Four stocks, reversible transitions, time and initial-cohort future T2D accounting; two survey candidate definitions; synthetic rates/allocation |
| Population conservation | Tested | Deaths and aging explicit; births/migration zero; 100-year test |
| Age/state mortality | Implemented with synthetic state ratios | Baseline mixture reproduces source schedule |
| Period life expectancy | Implemented and independently checked | NCHS all-age e_x reconstruction, 2022–2024 and three sex categories |
| Health-adjusted metric | Defined, implemented, arithmetic cross-checked | Age/state Sullivan years and restricted cohort time; 18 published NCHS values reproduced; synthetic metabolic state, not general HALE |
| Evidence-linked dietary effects | Plumbing implemented; scientific gate open | All inputs registered; coefficients/lag remain synthetic |
| Evidence completeness | Auditable | Status, unit, uncertainty, source metadata; missing entries reported |
| Authoritative mortality calibration | Pass | All-age e_x error below 0.001 year |
| U.S. diabetes/prediabetes prevalence | Benchmarks reconstructed; engine mapping unresolved | NHANES age/sex shares with survey uncertainty and 12 published cross-checks; total diabetes and glycemic states not silently relabeled as T2D/metabolic health |
| Historical backtest | Limited benchmark implemented | Frozen 2022 mortality predicts 2023; no diet-effect validation |
| Uncertainty propagation | Implemented | Seeded independent draws and paired scenario deltas |
| Sensitivity | Implemented | SALib Sobol indices with confidence half-widths |
| Tests and CI | Implemented | Offline test suite, lint, registry, CLI, and locked installation |
| Output provenance and restrictions | Implemented | Version/hash/vintage/flags; scientific mode disabled |
| Documentation and phase boundary | Implemented | Model spec, source pipeline, evidence gaps, full program vision |

## Observed validation results

The 2024 life-table reconstruction differs from the source by less than 0.00002 year at every age across the three sex categories. The 2022→2023 no-change mortality forecast underestimates total-population life expectancy by about 0.9645 year. This forecast error is reported; it is not tuned away or labeled a successful health prediction.

## Release gate

The [current issue #1 audit](ISSUE_1_AUDIT.md) and [clinical evidence appraisal](CLINICAL_EVIDENCE.md)
record six additional source-checked observational benchmarks. They remain separate
from active engine inputs and do not resolve the scientific gates in this table.

`uv run demeter validate --scientific-required` must fail for this alpha. Completing v0.1 requires the matched health evidence and calibration described in [EVIDENCE_GAPS.md](EVIDENCE_GAPS.md), plus an independent historical health validation. Do not tag a final 0.1.0 release based only on passing software tests.
