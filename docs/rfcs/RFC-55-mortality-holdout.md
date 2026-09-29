# RFC-55: Frozen mortality prediction on a reserved NHANES cycle

- Status: proposed
- Issue: [#55](https://github.com/Crusonia/Demeter/issues/55), supporting #1 and #27
- Author/date: Codex-assisted work for the Food is Health-affiliated project,
  September 29, 2026; personal human disclosures are not inferred
- Implementation: protocol and evaluator in progress; reserved outcomes not yet inspected
- Scientific assessment: research-backed descriptive assessment in progress;
  external expert review pending
- Scientific use: validation-only; clinical acceptance unresolved
- Relationship: extends the reserved-cycle component of [RFC-1](RFC-1-health-calibration.md);
  does not supersede its full health-calibration objective

## Scope and chronology

Estimate the predictive performance of the four already fitted 2011–2012 models
on NHANES 2013–2014 with the same public mortality release through 2019. This is
a baseline-category prediction benchmark for U.S. noninstitutionalized adults
meeting the frozen analysis domain. It does not identify causal current-state
mortality, state transitions, dietary effects, pediatric/oldest-age hazards or
national healthspan effects. Design traceability is I-01/I-11/I-12, F-08 and
T-01/T-05/T-06/T-08; no economic or externality pathway is activated.

Before retrieving any reserved outcome file, commit the protocol snapshot,
coefficient/covariance copies, evaluator, synthetic tests and input/code hashes.
Open a draft implementation PR with this record. The snapshot uses the existing
development receipt, not a new fit. Official baseline codebooks have been consulted;
their published baseline frequencies are not concealed. Reserved linked outcomes
have not been inspected in this work. Later corrections must preserve chronology,
disclose what outcomes were already seen and never recast used data as untouched.

## Frozen models, observations and sources

Retain `glycemic`, `null`, `glycemic_piecewise`, and `null_piecewise` exactly as
fitted in #53, including all eighteen coefficients and their joint covariance.
Use the existing likelihood/integration code, registered age knot, glycemic
cutoffs, diagnosis precedence, confidence level and numerical controls. Snapshot
these inputs and their implementation hashes; reject silent drift at runtime.
There is no optimization, intercept recalibration or choice of winning age form.

Retrieve official `DEMO_H`, `DIQ_H`, `GHB_H`, `GLU_H` XPORT files and the 2013–2014
2019-release public mortality file. Preserve the original bytes, exact URLs,
retrieval times, reuse conditions and checksums. Join in memory by SEQN after
checking unique identifiers and cycle membership; export only aggregates.

Use positive finite `WTSAF2YR`, `SDMVSTRA` and `SDMVPSU`. Apply the development
exclusions in their original order: adult minimum, known pregnancy, incomplete
glycemic observations, ineligible linkage, public top-coded age, missing sex,
and missing/nonpositive examination follow-up. Report every exclusion, remaining
age/sex/category support and follow-up range. Missing linkage is not survival.
The available pregnancy window and complete-case rules remain limitations.

The [GLU_H codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/GLU_H.htm)
documents a change of glucose laboratory/method from the development cycle.
Keep the prespecified measured-value definition and disclose this transport
limitation; do not invent a cross-laboratory correction or select one from
mortality outcomes. Its variable table names `WTSAF2YR`; the prose contains a
different spelling, so read the documented variable rather than guessing a field.

## Metrics and equations

For frozen model m, participant i, actual examination follow-up T_i in years and
death indicator delta_i, compute the existing analytic cumulative hazard H_im
and censored log score `l_im = delta_i log h_im(T_i) - H_im`.

For the overall eligible domain and each registered age × sex × baseline-category
domain, retain unweighted n/deaths, survey-weighted observed events O, integrated
event intensity E, their ratio R = O/E, mean log score and follow-up coverage.
E integrates over observed at-risk time. It is not a sum of event probabilities
at event-dependent follow-up, a common-horizon death risk or a diet prediction.

Report paired mean log-score differences for glycemic minus matching null within
each age form, and piecewise minus single-slope for both glycemic and null models.
Differences use the same participants and weights. Higher log score denotes
better relative predictive scoring for that comparison, not a causal effect.

All intervals estimate validation-sample uncertainty **conditional on these
frozen fitted models**. This estimand does not resample development coefficients.
Their entire joint covariance is retained in the snapshot for provenance; no
independent coefficient draws or claim of total uncertainty is made. Uncertainty
from confounding, model choice, measurement and transport is not identified here.

Use with-replacement Taylor linearization over every positive-weight design PSU,
including zero contributions outside each domain. For a weighted mean M, the
linearized contribution is `w_i d_i (y_i - M) / sum(w_i d_i)`. For R = O/E, it is
`w_i d_i (delta_i - R H_im) / E`. Sum contributions by PSU within stratum; the
variance is `sum_h [m_h/(m_h-1) sum_j (u_hj - mean_j u_hj)^2]`.
This follows [CDC's design and domain variance guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/varianceestimation.aspx).
Use the represented-domain PSU-minus-stratum degrees of freedom for the t interval,
while retaining the full design for its variance. Report design and domain support.
Compute positive O/E intervals on the log scale with delta SE `SE(R)/R`.

Empty domains, zero expected intensity, no observed events for a ratio interval,
nonfinite arithmetic or nonpositive domain degrees of freedom receive explicit
unavailable dispositions. They are not zero-width certainty or successful checks.
Reject malformed source data and singleton full-design strata. Retain sparse
domains descriptively rather than selecting favorable cells. An identical-model
score contrast is a defined exact zero; test that identity independently.

Intervals use the existing registered confidence level and are pointwise,
descriptive and not multiplicity-adjusted. No superiority hypothesis, p-value,
clinical pass threshold or multiple-comparison winner is declared. Neither a
positive point estimate nor an interval containing the target establishes clinical
acceptance. Report absolute discrepancies and all structural comparisons.

## Evidence changes and verification

Register `mortality_validation` as a derived, grade C, prediction-benchmark-only
dataset. Numeric model inputs remain the existing registered coefficients and
definitions, copied exactly into the immutable protocol. No active parameter,
distribution, equation or scenario changes. Source metadata and diagnostic output
are added to the catalog, rights and package inventory after intake.

Before outcome retrieval, test known analytic likelihood values, equality and
paired contrasts, independent hand-calculated PSU/domain variance, common-weight
scaling, empty/zero-event domains, definition/parameter/code drift and source
integrity failures using synthetic fixtures. Afterwards rebuild offline, reproduce
the aggregate receipt with declared floating-point tolerances, check source bytes,
and compare canonical engine results before/after under identical settings.
Keep numerical verification distinct from the reserved-cycle predictive results.

External expert review and clinical acceptance remain pending. The approved
[research-backed assessment path](../SCIENTIFIC_REVIEW.md) permits this descriptive
evaluation. The maintainer's merge disposition is separate. Rollback removes the
optional evaluator; retain the protocol and any inspected-outcome history.
