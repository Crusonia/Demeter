# RFC-56: Make the observation-to-state gap explicit

- Status: proposed
- Issue: [#56](https://github.com/Crusonia/Demeter/issues/56), supporting #1 and #27
- Author/date: Codex-assisted work for the Food is Health-affiliated project,
  September 29, 2026 (UTC); human disclosures are not inferred
- Implementation: optional report and CLI implemented; no active engine initialization change
- Scientific assessment: observation audit only; external expert review pending
- Scientific use: validation-only; national state initialization unresolved
- Supersedes: none; preserves existing NHANES and PreChronic definitions

## Question and scope

Which measured survey categories could inform the engine's initial health
stocks, and which observations or interpretations prevent that substitution?
Use the archived NHANES 2017–March 2020 noninstitutionalized adult fasting sample.
This advances I-01/I-07/I-11/I-12 and F-08 observation/validation design, with
T-01 accounting, T-05 alternatives and T-08 uncertainty/provenance checks.
No food, agriculture, economic or causal transition mechanism is added.

The current model labels and source classifications are not interchangeable.
The report supplies an auditable crosswalk and coverage, not fitted latent-state
probabilities or a national initializer. No unavailable relationship becomes zero.

## Definitions and alternatives

Reuse `nhanes_glycemic_prevalence.analysis` and
`nhanes_prechronic_candidates.analysis` without editing their classifiers or
thresholds. The registered `risk_1` and `risk_2` candidates remain alternative
observational rules, not separate populations to add together. Existing source
values have already been inspected; this is not an independent holdout.

Within complete cases, reported diabetes takes priority even if glucose is below
the diabetes thresholds. The diagnosis does not vanish with a normal measurement.
Both glycemic lab values remain required under the existing complete-case
benchmark. Record diagnosed people excluded by incomplete data explicitly.
Medication use and duration of control are not measured by this input contract;
normal measurements cannot establish treatment-induced remission.

The five PreChronic categories are disjoint by priority: any-type diabetes,
prediabetes, another listed reported diagnosis, normoglycemic earlier-risk
candidate, and lower measured risk. All remaining eligible records are explicitly
unclassified. A PreChronic candidate and glycemic prediabetes cannot overlap under
these definitions; non-glycemic risk markers may still coexist with prediabetes.

Retain the existing adult minimum, available pregnancy exclusion and survey
weights. Register the public age top-code from the
[P_DEMO codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DEMO.htm),
which prevents single-age decomposition in the oldest group. Do not replace
top-coded ages with a mean age or interpolate pediatric shares. Survey geography,
age coverage, period and the engine's target vintage remain explicit limitations.
The [P_DIQ codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DIQ.htm)
documents the interview coding; these observations do not identify diabetes type.

Alternatives requiring future evidence/RFCs include a partial-observation
classifier, validated type-specific diabetes algorithm, explicit diagnostic
error model, and a redefinition of the engine's stocks. None is silently selected.

## Estimation and evidence change

Add `observation_state_mapping` as a derived grade-C, benchmark-only dataset,
with the crosswalk, coverage restrictions and source-codebook links. Reuse all
existing clinical thresholds and confidence levels. The only new numeric
definition is the observed public age top-code; no clinical coefficient or
distribution changes. Original source files and rights remain unchanged.

For each registered age/sex domain D and observed category C, report
`sum(w D I[C]) / sum(w D)`, with the existing Taylor logit-t survey interval.
The denominator includes unclassified eligible people. Unlike a complete-case
prevalence, these proportions plus the unclassified share sum to one. Missing
category membership is not allocated to healthy or rescaled away. Show the
unweighted support and weighted denominator as coverage diagnostics.

Retain all positive-weight survey PSUs, including zero domain contributions.
Intervals are marginal and share respondents; they do not describe independent
initialization draws, item-nonresponse bias, definition or transport uncertainty.
Boundary/empty/insufficient-variance intervals remain explicitly unavailable.
Registered overlapping age domains and the two alternatives cannot be summed.

The crosswalk records a candidate engine label, its meaning mismatch and an
explicit rejection of direct initialization. Prediabetes may match the optional
four-state observation label, but missingness and population/vintage transport
still prevent claiming an evidence-supported national initializer. Other
diagnoses and unclassified respondents must not disappear from population totals.

## Verification and disposition

Before coding, plan checks for partition conservation, retained missingness,
diagnosis precedence below lab thresholds, complete-case selection, alternative
definition nesting, pediatric/top-code coverage and absent inference of diabetes
type. Independently hand-check a synthetic weighted partition and compare real
coverage with the existing NHANES/PreChronic bundles. Rebuild offline with exact
source receipts, verify registry and implementation provenance, and verify
canonical engine outputs are unchanged. Numerical reproduction does not validate
the crosswalk as a latent-state measurement model.

Software assessment: focused partition, missingness and offline reconstruction
checks pass; all 435 Python tests, Ruff and the evidence-package audit pass. Scientific assessment:
[executed observation audit](../OBSERVATION_STATE_MAPPING.md); external expert
review pending. Maintainer disposition: pending.
Rollback removes the optional report; no engine migration is needed. Issue #56
remains open for evidence-supported initialization, including type, age, missing-
data and temporal transport decisions. This RFC cannot satisfy those requirements
by documenting that they are missing.
