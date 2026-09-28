# RFC-1: Observation mapping and health calibration

- Status: proposed
- Issue and PR: [#1](https://github.com/Crusonia/Demeter/issues/1), [draft #53](https://github.com/Crusonia/Demeter/pull/53)
- Author/date: Codex-assisted proposal, September 28, 2026; no human scientific authorship or approval inferred
- Implementation: source audit and optional development prediction fit implemented; engine mapping and clinical acceptance not implemented
- Scientific assessment: pending; no named expert assessment supplied
- Scientific use: validation-only
- Supersedes: none

## Question and full scope

Can the U.S. dietary exposure → metabolic state → mortality → longevity model
satisfy the complete [issue #1 objective](../CODEX_V0_1_OBJECTIVE.md) with credible
initial states, transition/mortality hazards, exposure effects, uncertainty and
independent historical validation? Mortality evidence intake is one component;
an adult association model alone cannot complete this objective.

Traceability: I-01 health foundation, I-07 progression, I-11 measurement, I-12
experiment controls; F-01 conservation, F-04 exposure, F-08 observation;
T-01/T-02 arithmetic, T-03 convergence, T-05 alternatives, T-06 holdouts,
T-08 uncertainty/applicability. L-00 is the current health foundation. Q-03 and
RM-04 are downstream motivations, not evidence of a PreChronic or payer effect.
Value-chain/externality X- contracts are inapplicable to this Phase 1 study.

## Identification finding

The [executed diagnostic](../validation/issue-1-mortality-identification.json)
uses the two endpoints of the existing registered synthetic mortality-ratio
ranges. Both parameterizations reproduce initial NCHS mortality and life
expectancy to numerical precision, yet their later trajectories differ. This
is a counterexample to identifying state-specific hazards from the aggregate
life-table fit. It is not evidence for either parameterization.

Reproduce it from the repository root with
`uv run python scripts/mortality_identification.py`. The default output is
`outputs/mortality-identification.json`; the checked-in receipt preserves the
original run's source commit. Compare numerical results with floating-point
tolerance across platforms, and compare the evidence hash before interpreting
differences. This is a diagnostic, not a clinical acceptance test.

For baseline shares w_s and mortality hazards h_s, the model matches

`q_x = sum_s w_xs * (1 - exp(-h_xs))`.

One observed death probability cannot identify the state decomposition. Similarly,
cross-sectional prevalence constrains stocks, not the opposing progression and
reversal flows. Priors or a chosen optimizer do not create those observations.

## Observation contract and alternatives

| Observation | Permitted use | Mapping that must not be assumed |
| --- | --- | --- |
| NHANES joint A1c/FPG normoglycemia | Survey-defined glycemic category with diagnosis precedence and complete-case selection | Overall metabolic health or absence of insulin resistance |
| NHANES joint A1c/FPG prediabetes | Defined survey intermediate category | The engine's entire IR population |
| Survey all-type diabetes | All-type glycemic/diagnosis burden | T2D without type identification or a validated measurement model |
| Baseline glycemia plus linked death | Baseline-category survival association | Causal mortality hazard of entering/leaving a current state |
| ARIC follow-up glycemia | Definition-, population- and follow-up-specific transitions | National annual hazards for every age/sex |
| Dietary prospective association | Endpoint/dose-specific association | A causal modifier for two different transition hazards |

The proposal keeps observations distinct from the existing engine stocks.
No relabeling or direct substitution is approved. A future operational glycemic
state definition is an alternative requiring explicit semantic migration and
tests, including treatment-controlled diabetes and diabetes of other/unknown
types. It must preserve total population and report the unclassified remainder.

Survey diabetes-type algorithms are possible sensitivity definitions, not gold
standards. The [primary comparison of survey algorithms](https://drc.bmj.com/content/8/2/e001917)
shows why age/insulin rules and self-report need appraisal. Do not classify all
undiagnosed diabetes as T2D, or infer uninterrupted insulin use from a duration
answer. No algorithm sensitivity/specificity is invented here.

The [corrected ARIC article](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2775594)
contains follow-up glycemic counts, competing deaths, varying visit times and
nonattendance. Its Figure 2 distribution must not be treated as a fully observed
national fixed-time transition matrix or divided by a median follow-up to create
annual hazards. Joint visit-time, censoring, definition and attrition information
is needed to specify an estimable transition likelihood.

## Proposed mortality development protocol

This is a proposed baseline-category prediction benchmark, not the engine's
causal state mortality calibration. It tests whether the new public-data route
can supply useful out-of-sample evidence; failure stays visible.

- Development: NHANES 2011–2012 with public mortality through 2019, already
  inspected. It can never be called an untouched holdout.
- Reserved temporal validation: NHANES 2013–2014 with the same 2019 public
  mortality release. Its linked outcomes have not been inspected in this work.
  Public availability or baseline inspection elsewhere is not a claim that the
  outcomes were blinded in all prior research. Freeze this protocol before
  extracting those outcomes; never retune on them while calling them held out.
- Domain: complete adult baseline glycemia with positive fasting weight, known
  pregnancy excluded using registered rules, linkage eligible, positive observed
  examination follow-up. The public top-coded age group is reported separately
  and excluded from a model requiring exact attained age. This restriction does
  not satisfy the national/pediatric/oldest-age part of issue #1.
- Retain every positive-weight PSU in variance calculations. Report exclusions
  separately for missing glycemia, linkage, age and follow-up. Evaluate linkage
  and complete-case selection; do not assume original weights correct them.
- Candidate prediction model: Gompertz attained-age hazard with sex and baseline
  glycemic category, compared with an age/sex-only null. There are no dietary
  coefficients and no inferred state transitions in this benchmark.

With t in years since examination, a_i baseline age and indicators z_i for sex
and baseline categories, the proposed hazard is

`h_i(t) = exp(b_0 + b_a*(a_i + t - a_ref) + b_z*z_i)`.

`a_ref` is the registered adult minimum, a centering convention. Integrate this
hazard analytically for each participant's actual reported follow-up; use its
continuous limit when b_a is zero. Fit the weighted censored log-likelihood
`sum_i w_i * [delta_i*log(h_i(T_i)) - integral_0^T_i h_i(t) dt]`.
Respect event/censoring indicators and source disclosure perturbation. Use
survey-design score aggregation/sandwich covariance rather than treating weights
as replicated independent people. Zero follow-up receives an explicit unresolved
disposition, never an arbitrary half-month addition. Missing records are not
assigned survival or healthy status.

Before implementing: register coefficient roles, units, estimator, bounds if any,
uncertainty method and numerical controls. Numerical fitting is authorized as a
validation-only experiment, not evidence promotion. A convergence failure,
singular information matrix, sparse domain, materially prior-driven parameter or
unresolved observation mapping cannot be converted into a successful fit.

### Development implementation record

The `mortality_development` dataset registers the numerical controls and eighteen
`mortality_development_*` benchmark coefficients. The Gompertz candidate and
age/sex-only null use unbounded coefficients, no priors, an initial constant-rate
intercept estimated from weighted deaths/person-time, and zero initial slopes.
Trust-region Newton optimization uses the analytic score and Hessian. Small-slope
analytic integrals use a registered series expansion to avoid cancellation.
The score-sandwich retains all positive-weight PSUs, including zero-score PSUs
outside the selected domain; no finite-population correction is assumed.
The reported joint covariance and t intervals cover sampling uncertainty only.

For censored data, the observed/expected diagnostic compares deaths with the
integrated hazard over actual observed risk time. Summing death probabilities
at each person's event-dependent follow-up would not be the same diagnostic.
An intercept fit forces aggregate event balance in development; that balance
is not an independent acceptance result. Subgroup residuals are descriptive.

The [development record](../MORTALITY_DEVELOPMENT.md) reports the executed fit,
numerical checks, source exclusions and unresolved selection/transport issues.
Its coefficients are baseline-category associations and remain benchmark-only.
Neither positive in-sample likelihood gain nor a confidence interval permits
their substitution for the model's current-state mortality ratios.

## Validation and acceptance plan

### Alternative age form declared before its fit

On September 28, after inspecting the original Gompertz development results and
the automated review finding, select a continuous piecewise-linear log hazard
in attained age with one hinge at age 60. This uses the existing survey older-age
domain boundary, not a cutpoint selected from mortality residuals. The declaration
is prospective for the alternative fit, not a claim it preceded the original fit.
The 2013–2014 reserved outcomes remain uninspected.

Add `b_h * max(a_i + t - 60, 0)` to the log hazard. Fit both glycemic and age/sex-only
versions with this same age form. Integrate exactly across the hinge and retain
the original single-slope fits. Register the knot as a modeling convention and
all ten additional benchmark coefficients before estimation. Report the change
in glycemic coefficients, intervals and in-sample likelihood without selecting
a winner from development likelihood or calling stability clinical validation.
Test split-time integration against independent quadrature, score/Hessian
derivatives across the hinge and reduction to the original form when `b_h=0`.

1. **Numerical:** test integrated hazards against independent quadrature,
   zero-age-slope limits, finite likelihoods and analytic/finite-difference scores.
   Check invariance to common weight scaling and correct empty-domain PSU handling.
2. **Development:** report estimates with covariance, residuals, event counts,
   weighted predicted/observed mortality and age/sex/category support. Preserve
   the no-state-effect null and meaningful alternative age specifications.
3. **Reserved cycle:** freeze coefficients and observation definitions. Evaluate
   censored predictive log likelihood versus the frozen null, predicted/observed
   deaths and survey-aware uncertainty by supported domain. Account for different
   follow-up durations; do not compare crude fractions as equal-duration risks.
4. **Rejection:** no improvement over the null, evidence of subgroup miscalibration,
   unstable estimation, or failure to transport definitions rejects promotion.
   A favorable aggregate score cannot excuse unsupported subgroups or causality.
   Evaluation metrics and any evidence-justified tolerances must be registered
   in the research-backed validation report before holdout inspection. External
   expert review may remain pending. Clinical tolerances are currently unresolved;
   descriptive predictive evaluation may proceed under a frozen protocol, but
   cannot imply clinical acceptance. No pass threshold is chosen from holdout residuals.
5. **Full issue #1:** separately resolve age/sex initialization, T2D identification,
   compatible progression/reversal, current-state mortality, dietary dose/endpoint
   and lag, uncertainty dependence, and a forward health holdout. This benchmark
   cannot stand in for those requirements even if its predictive checks pass.

## Evidence changes and use boundaries

| Key | Current state | Proposed change before fitting |
| --- | --- | --- |
| nhanes_linked_mortality | Derived grade C feasibility-only audit; source-pinned 2011–2012/2019 | Retain; append separately versioned protocol/fit/validation artifacts |
| mortality_development_* | Initially unresolved proposed coefficients | Estimated grade C benchmark coefficients with joint survey covariance; no engine promotion |
| initial_*_share | Synthetic grade E | No promotion; observation mapping, population coverage and vintage unresolved |
| h_to_ir_rate, ir_to_h_rate, ir_to_t2d_rate | Synthetic grade E | No promotion; compatible longitudinal likelihood needed |
| mortality_ir_ratio, mortality_t2d_ratio | Synthetic grade E | No promotion from aggregate fit or baseline-category regression |
| beta_upf_progression, diet_lag_years | Synthetic grade E | No promotion; joint dose/endpoint/lag evidence needed |

No active engine coefficient, distribution, bound or equation changes. The
[source audit](../LINKED_MORTALITY.md) records data units, weights, missingness,
uncertainty, receipts and reuse terms. Registered synthetic stress endpoints in
the identification diagnostic are not empirical estimates. Competing sources
and definitions must be compared; choosing the largest benefit is prohibited.

## Review, objections and disposition

Software assessment: source intake tested; independent review pending.
Scientific reviewer, expertise, independence and conflicts: not supplied.
Maintainer disposition: Carter Williams approved the research-backed assessment
path on September 28, 2026; implementation and evaluation may proceed with
external expert review pending. Scientific acceptance of the full model remains
unresolved. PR merge disposition remains separate.
Author disclosures: AI-assisted work in the Food is Health-affiliated project;
no human conflict disclosure or independent assessment is inferred.

| Objection | Response and required evidence | Disposition |
| --- | --- | --- |
| A good life-table fit is sufficient | Executed counterexample shows different decompositions fit identically | Rejected as a sufficiency claim |
| The public mortality regression can replace current-state hazards | It conditions on baseline category and includes later state changes | Unresolved; no promotion |
| A survey algorithm resolves T2D | Definition comparison and validated error/transport evidence are required | Unresolved |
| Older-cohort aggregate transitions suffice nationally | Visit timing, competing risks, missingness and transport must be modeled | Unresolved |
| A green PR permits scientific release | Repository policy requires scoped scientific assessment and acceptance tests | Release remains blocked |

The approved [review policy](../SCIENTIFIC_REVIEW.md) now permits a research-backed
validation report while external expert review is pending. See the
[claim/evidence assessment](../EVIDENCE_VALIDATION_REPORT.md). This removes the
reviewer-recruitment prerequisite, not the missing evidence or scientific tests.
Rollback is removal of the optional benchmark; existing engine semantics and
scientific gate remain unchanged.
