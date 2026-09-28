# Issue #1 research-backed evidence and validation assessment

Status: implementation/evidence assessment in progress; external expert review
pending. Author: Codex-assisted analysis for the Food is Health-affiliated project.
No independent human assessment, clinical endorsement or full v0.1 acceptance is
claimed. Carter Williams approved this assessment path on September 28, 2026.

## Framework and scope

This report applies the [ISPOR–SMDM model transparency and validation framework](https://pubmed.ncbi.nlm.nih.gov/22999134/):
code verification, expert assessment, model comparisons, external validation and
predictive validation are separate evidence categories. Published methods guide
the assessment; they do not certify Demeter. This report replaces reviewer
recruitment as a prerequisite to progress under the [approved policy](SCIENTIFIC_REVIEW.md).
It preserves the full [issue #1 objective](CODEX_V0_1_OBJECTIVE.md).

## Claim-to-evidence assessment

| Claim or mechanism | Available evidence and reproducible check | Current conclusion and missing work |
| --- | --- | --- |
| Age/sex mortality and period life-table arithmetic | Archived CDC/NCHS life tables, Census initialization, nine reconstruction checks and independent arithmetic fixtures; `demeter validate`, `tests/test_life_table.py`, `tests/test_cohorts.py` | Numerical reproduction supported within documented tolerance. Synthetic state ratios are not identified by this match. |
| Survey glycemic prevalence | [NHANES reconstruction](NHANES_PREVALENCE.md), archived labs/interviews, survey weights, published table comparisons | Observation reconstruction supported. Normoglycemia, prediabetes and all-type diabetes do not automatically identify metabolic health, insulin resistance and T2D engine stocks. |
| Baseline-category mortality prediction | [Development benchmark](MORTALITY_DEVELOPMENT.md), 2011–2012 NHANES/2019 linkage, four fitted models and joint survey covariance | Estimation and numerical checks performed. No independent prediction validation yet; selection, perturbed follow-up and transport remain unresolved. |
| Dependence on age specification | Original Gompertz versus continuous piecewise attained-age log hazard, each with matched age/sex null; analytic integration and independent numerical checks | Alternative is implemented after the original development fit, with declaration before alternative fitting. Both results retained; coefficient changes disclosed. No model selected or clinically accepted from this comparison. |
| Progression and reversal | Corrected ARIC/LEADR estimates and [clinical appraisals](CLINICAL_EVIDENCE.md) | Population, endpoint, follow-up and competing-risk mismatches remain. No national current-state transition likelihood is established. |
| Dietary intervention, dose and lag | Archived dietary baselines; [Look AHEAD response challenge](DIET_DYNAMICS.md); candidate prospective evidence | Observed intake and a multicomponent trial do not identify the current UPF coefficient, both progression pathways or the lag. Engine parameters remain synthetic. |
| Longevity/healthspan response | Life-table and Sullivan arithmetic plus registered method checks | Arithmetic supported. A clinical dietary or healthspan effect is not established by synthetic scenarios. |
| Uncertainty and sensitivity | Paired seeded simulations, SALib/Sobol tests, benchmark joint covariance | Mechanics work for declared distributions. Structural, transport and causal uncertainty remain incomplete. |
| Forward health prediction | [Historical backtests](BACKTESTING_STRATEGY.md), frozen-mortality comparison, temporal leakage tests | Limited benchmark predictions exist. No independent end-to-end diet → metabolic state → mortality validation exists. |

Source URLs, publisher/vintage, original hashes, transformations and reuse terms
remain in the registry, data catalog, source manifests and rights inventory.
The [development receipt](validation/issue-1-mortality-development.json) is the
numerical record, including uncertainty and subgroup diagnostics. Raw files are
unchanged and no joined person-level file is exported.

## Structural comparison and objections

The automated review of `430dc25` identified the missing promised alternative
age specification. The implemented response adds a continuous slope change at
age 60, an existing survey domain boundary chosen before the alternative fit.
The original fit had already been inspected; this chronology is disclosed in
[RFC-1](rfcs/RFC-1-health-calibration.md). It is not an untouched development test.

The prediabetes log-hazard coefficient changes from approximately -0.129 to -0.090;
the all-type diabetes coefficient changes from 0.740 to 0.797. The complete
intervals, covariance and same-age-null likelihood comparisons are retained.
These are development associations, not intervention effects. The report makes
no arbitrary claim that the change is acceptably small. The original estimates
remain exactly reproducible, and neither alternative is selected as the winner.

Code checks compare integrals with independent adaptive quadrature, compare
scores/Hessians with numerical derivatives, test crossing the age knot, confirm
the zero-hinge reduction, preserve weight-scale invariance and empty-domain PSUs,
and reject nonconvergence or unidentified information. These checks do not test
unmeasured confounding or supply missing state-transition observations.

## Next validation record, before reserved outcomes are inspected

The reserved NHANES 2013–2014/2019 linkage remains uninspected in this work.
Further descriptive validation may proceed without an external expert once its
executable protocol is frozen. The record must fix source versions, observation
definitions, the four development fits, exclusions, domain handling, numerical
controls, coefficient uncertainty treatment and the following metrics:

- Paired censored log-score differences against the null with the same age form.
- Observed deaths versus integrated event intensity over observed risk time,
  with survey-aware uncertainty and subgroup support.
- Differences across the two age forms, without retuning on the reserved cycle.
- Missingness, linkage selection, follow-up and age coverage diagnostics.

Any test of statistical superiority must declare direction, uncertainty method
and multiplicity handling before use. A clinical tolerance requires a defensible
source or explicit rationale before outcome inspection. If unavailable, results
remain descriptive; absence of statistical evidence of miscalibration is not
proof of clinical equivalence. No metric or cutoff is selected to obtain a pass.
If model changes follow outcome inspection, that cycle becomes used evidence and
cannot be described as an untouched holdout for the revised model.

## Disposition

The lack of a named human reviewer is no longer a prerequisite blocking evidence
collection, implementation or predeclared evaluation. External expert review
remains pending and is not impersonated by this report or by automated review.
The policy approval is recorded separately from PR merge authority.

Current supported conclusions are limited to source reconstruction and numerical
development estimation. Independent mortality prediction, engine state mapping,
causal dietary pathways and full scientific v0.1 acceptance remain unresolved.
The release gate stays false for those substantive reasons. Closing issue #1
still requires its full acceptance evidence; this report is the record through
which that work proceeds, not a replacement for it.
