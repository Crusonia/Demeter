# Clinical observation contract

Status: design input for [#57](https://github.com/Crusonia/Demeter/issues/57)
and [#58](https://github.com/Crusonia/Demeter/issues/58). This document specifies
what a source-to-model review must resolve before clinical fitting or state
activation. It introduces no clinical thresholds, empirical values, active
parameters or observation-model implementation.

The executable [DPP preservation adapter](DPP_OBSERVATION_ADAPTER.md) implements
strict normalized observation objects and aggregate software diagnostics. It
preserves measurements and unknowns; it supplies no clinical likelihood, inferred
state or fitted parameter. Public documentation receipts and synthetic checks
are separate from participant-record coverage and scientific validation.

The [DPP source coverage matrix](DPP_SOURCE_COVERAGE.md) records exact public
field/form locators, excluded dates and version discrepancies. It distinguishes
documented meaning from actual record coverage and identifies which proposed
clinical fits remain unsupported under the public-source route.

The [Stanford iPOP source appraisal](IPOP_SOURCE_COVERAGE.md) verifies selected
headers, producer operations and assay-name identity. It records full binary
acquisition separately from limited inspection, including a failed text-request
scope exception. Subsequent review of Zheng et al. (2022) establishes public
provenance for the named derivative. A native-cohort laboratory-panel intake is
possible under predeclared measurement and relative-day assumptions; rawness,
specimen association and actual record coverage still need assessment. Unknown
additive clock origin alone does not block within-person elapsed differences.
No clinical fit, diagnosed-state mapping or national activation follows from this
appraisal.

The [Whitehall II endpoint implementation](WHITEHALL_ENDPOINT.md) reproduces
published source labels and evaluates a conditional iid binomial working
likelihood. Its fitted endpoint probability is separate from clinical transition
parameters. The source does not establish that sampling model or resolve latent
states, histories, exact timing, selection, competing death or U.S. transport.
It therefore does not satisfy the full clinical observation contract below.

The [paired remission observation model](PAIRED_REMISSION_OBSERVATIONS.md)
implements integer constraints on two visits' source labels, conditional on
explicit common-cohort and positive-subgroup scope. It preserves diagnosed-T2D
history, source failures and unknown assessment/death partitions. It supplies
neither a latent clinical likelihood nor an annual hazard fit; exact observation,
treatment, censoring and clinical identification requirements below remain open.

The [linked-path software evaluator](LONGITUDINAL_LIKELIHOOD.md) implements declared
panel, first-entry timing, competing-death and censoring kernels with frozen
synthetic checks. It confers no source eligibility and performs no clinical fit.
Its continuous-time kernels remain separate from the annual simulation engine;
actual observation coverage and scientific acceptance requirements below remain open.

The [project vision](PROJECT_VISION.md), [architecture](SYSTEM_ARCHITECTURE.md)
and [scenario catalog](SCENARIO_CATALOG.md) preserve the broader program. The
current work remains within the v0.1 health slice. Its design chain is the health
part of Q-03/RM-04 → P-02 → I-01/I-05/I-07/I-11/I-12 → F-04/F-08 →
T-01/T-05/T-06/T-08 in the [design registers](design/README.md). L-00 supplies
stock/flow bookkeeping, not clinical evidence. The payer-cost part of P-02,
business externalities, value capture and stakeholder-belief tests are
inapplicable to this observation contract. Design premises are not empirical
parameters or implemented capabilities.

## Current mechanics and the missing clinical layer

The [current model](MODEL_SPEC.md) applies annual mortality, transitions among
survivors, then aging. A survivor makes at most one endpoint transition during
that operator step: healthy-to-IR entrants cannot also enter diabetes in the
same step. The legacy states are metabolically healthy, IR/prediabetes proxy and
type 2 diabetes; that structure has no diabetes-remission flow. Optional
PreChronic mechanics remain synthetic and do not establish clinical categories.

A laboratory category is an observation, not automatically an engine state.
Normal glycemia does not establish general metabolic health; prediabetes does
not measure every form of insulin resistance; an unspecified diabetes diagnosis
does not establish type 2 diabetes. A later low glucose observation does not
erase diagnosis history or establish sustained remission. Follow the
[state mapping](OBSERVATION_STATE_MAPPING.md) and
[partial-observation rules](PARTIAL_OBSERVATIONS.md) before allocating people.

A future clinical observation model would connect latent states, diagnosis
history and exposures to recorded measurements, visit times, confirmation and
stopping. It must be specified separately from the annual engine. A panel
transition probability, a first-diagnosis Cox hazard ratio and an annual
survivor flow describe different quantities. The executable
[Reus compatibility diagnostic](../src/demeter/analysis/pathway_compatibility.py)
tests the existing operators with synthetic inputs; it supplies no clinical
likelihood or fitted effect.

## Reusable source review

For each candidate package, fill this table with exact source locators,
registry keys and an explicit unresolved entry where information is absent.
Link to immutable receipts rather than copying individual records into the
review. The [input register](design/04_MODEL_INPUTS.md) and
[formulation/test register](design/05_FORMULATION_AND_TESTS.md) define the stable
IDs used here.

| Record | Required source-backed content | Consequence if unresolved |
| --- | --- | --- |
| Identity and permission | Primary publication/release, correction/version, population, geography, period, rights, exact table/variable locators and byte hashes; reproducible separation of raw, derived and model-ready data | No unverified intake or distribution; a related report cannot silently substitute |
| Estimand and comparator | Outcome, starting population, time origin/horizon, intervention/comparator, assignment versus adherence, total versus conditional effect, causal versus associational interpretation | Retain the supported source estimand; do not rename it a transition effect |
| Baseline and selection | Recruitment, eligibility, age/sex, glycemic observations, prior diagnosis/type, treatment, sampling/selection and denominator | No invented initial-state allocation or national transport |
| Exposure | Offered, purchased and consumed quantities distinguished; definitions, units, range, timing, substitutions, adherence and cointerventions | A food/regimen label cannot become a UPF dose, lag or coefficient |
| Measurement and thresholds | Assay, fasting/test conditions, units, calibration, source-specific diagnostic algorithm and its version; sourced threshold/algorithm registry references before use | No category conversion or guessed cutoff; preserve compatible observation sets |
| Confirmation and history | Repeat-test/symptom rules, prior diagnosis, medication use, type classification, index versus confirmation date; persistence and treatment-free duration if remission is claimed | No fabricated diagnosis date, reversal or remission endpoint |
| Visits and ascertainment | Entry, collection, result and visit dates/windows; last negative, first positive and confirmation; missed tests and whether observation timing is fixed, ignorable or informative | No unsupported scheduled-panel likelihood or inferred biological onset |
| First event and stopping | Biological onset versus detection/confirmation; exact, interval or right-censored time; final-measurement alignment and administrative end rules | Restrict to identifiable recorded events or descriptive counts |
| Treatment and causal role | Starts/stops/intensity, cointerventions and changes during follow-up; confounder, mediator or outcome role relative to the chosen estimand | No automatic total-causal interpretation of postassignment adjustment |
| Death, loss and withdrawal | Competing death time/resolution, last contact, withdrawal/loss reason, at-risk denominator and censoring assumptions | Do not treat unobserved competing events as absent or censoring as independent by default |
| Missingness | Eligible denominator, missing/invalid/refused/unknown codes, missing visits and categories; justified selection/imputation assumptions and alternatives | Preserve unknowns; no silent deletion, zero replacement or point allocation |
| Dependence and uncertainty | Interval type, sampling design, repeated participants, shared controls, overlapping reports/reanalyses, joint covariance or its absence | No independent pooling or invented joint draws from marginal intervals |
| Likelihood and identification | Observable versus latent quantities, measurement error, conditioning/selection, time units, event process, structural alternatives and which parameters can be distinguished | Keep unidentified quantities unresolved rather than fitting a convenient explanation |
| Evaluation and applicability | Used-source chronology, calibration/evaluation split, independent target, metrics, justified tolerances, population/exposure overlap and extrapolation | Reproduction is not independent validation; unsupported transport remains blocked |

## Likelihood requirements

The [RFC-57 identification proposal](rfcs/RFC-57-longitudinal-identification.md)
and [Chen timing RFC](rfcs/RFC-57-chen-timing-and-observation.md) describe possible
continuous-time observation models. The following are candidate contracts, not
active Demeter equations. Here Q is a generator; A is its transient subgenerator
before a specified absorbing recorded event; r_D contains hazards into that
event. Rates and densities have reciprocal-time units; probabilities do not.

| Observation mode | Candidate contribution and condition |
| --- | --- |
| Exogenous or ignorable panel | A mapped entry of `exp(Q t)`; justify observation timing conditional on recorded history, or include the observation process in a joint likelihood |
| Exact first recorded event | `[exp(A t) r_D]_i`; sum over unobserved transient paths and justify entry, ascertainment and stopping. Exact detection is not exact biological onset |
| Interval-detected first event | Integrate the first-event density over the supported interval, conditional on the actual observation history and correct time origin; a last-negative measurement and no-diagnosis history impose different information |
| Non-event endpoint | `[exp(A t)]_ij` is the joint probability of no absorbing event and transient endpoint j, with justified observation/censoring. Normalize only if the sampling/conditioning contract requires it |
| Unknown state or event status | Sum over compatible observations under an explicit missingness/measurement model; missing history supplies no invented transition |

These expressions require appropriate state/measurement mapping and any relevant
selection contribution. Death can require a separate absorbing destination;
treatment and informative visits can require time-varying or joint processes.
Measurement-error parameters require evidence or identification analysis of
their own. None of this asserts that `exp(Q)` equals the implemented annual
operator, or that a reported adjusted Cox ratio is a state hazard multiplier.
Reconstructing a Cox fit also requires its risk sets, covariates and source
event/stopping definitions.

## Evaluation and failure disposition

Before inspecting reserved outcomes, freeze observation definitions, source
inclusion and alternatives, transformations, estimands, model/likelihood,
calibration targets and evaluation metrics. Label protocols written after
outcome inspection as used-source work. Verify units, conservation, bounds,
source integrity, unknown/history handling and likelihood-mode consistency.
Use labeled synthetic recovery experiments, sensitivity/rank or profile checks,
nulls and structural alternatives to expose what the proposed observations can
distinguish. Compare supported independent observations at their actual temporal
and population resolution. Separate numerical, sampling, measurement,
structural and transport uncertainty.

No clinical acceptance cutoff is supplied here. If a defensible tolerance cannot
be sourced or justified, report diagnostics descriptively and leave acceptance
unresolved. Apply the [scientific review process](SCIENTIFIC_REVIEW.md); passing
software checks and automated critique are not independent human review.

| Failure | Disposition |
| --- | --- |
| Source/version/rights cannot be verified | Keep the intake unresolved and preserve only permitted receipts |
| Published benchmark and release disagree | Retain the failed check and exact provenance; do not rescale, trim or redefine the target to obtain agreement |
| State, timing or stopping does not support a likelihood | Block the dependent fit/activation; retain supported descriptive observations and pursue a compatible package |
| Parameters remain indistinguishable or the effect is confounded | Preserve alternative explanations and labeled synthetic witnesses; do not promote an estimate to an active coefficient |
| Treatment, competing events or covariance are missing | Narrow the claim to what is supported; no unsupported mediation, competing-risk or independent-pooling result |
| Evaluation data were reused or the model changed after inspection | Record used-source status and freeze a new evaluation rather than relabeling the old result independent |
| Population or exposure transport lacks support | Retain a source-specific benchmark; do not allocate a national state or intervention effect |

These are review dispositions, not new evidence statuses. Substantive numeric
inputs still require the evidence registry and its existing status, provenance,
units and uncertainty rules. An unresolved Chen timing question need not stall
other public-source work; it continues to block only conclusions that depend on
that timing contract.

## Current Reus disposition

The [Reus assessment](REUS_DIABETES_PATHWAY.md) and
[source/compatibility RFC](rfcs/RFC-58-reus-source-and-compatibility.md), extending
[RFC-58](rfcs/RFC-58-food-pathway-identification.md), retain the original report
and its correction as distinct, overlapping analyses. They support reproduction
of the reported overall adjusted first-diabetes comparisons and uncertainty in
the selected older, high-cardiovascular-risk Spanish population without baseline
diabetes. The corrected analysis excludes nonrandomized household partners.
The assigned intervention combines dietary counseling with offered foods;
offered quantities do not establish consumed UPF exposure.

The source's diagnostic testing, confirmation and diagnosis/death/final-visit
stopping require a compatible observation model. First-positive versus
confirmation timing remains unresolved. Adjustment for weight change during
follow-up prevents automatic interpretation of the reported coefficient as a
total causal regimen effect; the original and correction adjustment footnotes
also differ. Shared controls and overlapping participants prevent treating the
reported comparisons as independent studies. Marginal intervals do not supply
joint covariance.

Current public aggregates do not reconstruct the adjusted Cox fit or distinguish
healthy-to-IR progression, IR-to-diabetes progression and recovery effects. They
do not identify UPF dose/lag, remission, mortality, U.S. or PreChronic transition
rates, or healthcare-cost effects. The frozen
[source protocol](validation/reus-diabetes-protocol-v1.json) and
[compatibility amendment](validation/reus-diabetes-amendment-1.json) support
used-source extraction and operator-specific synthetic witnesses only. A future
clinical bridge needs the applicable records above and an evaluation matched to
its claimed endpoint. Neither #57 nor #58 is closed by this design input;
external expert assessment and v0.1 scientific acceptance remain pending.
