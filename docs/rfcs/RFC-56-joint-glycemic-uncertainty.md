# RFC-56 extension: joint uncertainty of observed glycemic categories

Status: proposed; October 1, 2026 UTC. Supports #1/#27 and the unresolved
initialization requirement of #56. Author: Codex-assisted work for the Food is
Health-affiliated project. External expert review pending; no independent human
review or clinical-state acceptance is claimed.

## Question and boundary

What sampling covariance accompanies the existing NHANES observed-category
partition, including unknown observations and overlapping age/sex domains?
Separate marginal intervals cannot supply independent initialization draws.
This advances I-01/I-07/I-11/I-12, F-08 and T-01/T-05/T-08 in the
[design registers](../design/README.md). No causal effect, transition, dietary
mechanism or active engine initializer is added.

Reuse the archived 2017–March 2020 fasting sample, existing glycemic thresholds,
diagnosis priorities, eligible adult/pregnancy rules and registered age/sex
domains. Preserve the complete-case classifier and partial-observation helper
unchanged. Complete categories are normoglycemia, prediabetes, diabetes of any
type and unclassified. Partial categories are the seven nonempty subsets of
the three glycemic labels, fixed before numerical execution. Their disjoint
pattern proportions sum to one; overlapping possible-category columns do not.

The source and prior point estimates have already been inspected. The frozen
[protocol](../validation/joint-glycemic-uncertainty-protocol-v1.json) precedes
new covariance execution, but this is used-source analysis, not preregistration
or an independent holdout. No new participant records are acquired.

## Formula and uncertainty

For coordinate k, define its domain D, binary category indicator Y, weight w
and weighted proportion p. Linearized contribution for respondent i is
`u_ik = w_i D_ik (Y_ik - p_k) / sum_i(w_i D_ik)`.
Sum these vectors by masked stratum/PSU to T_hj. Compute
`V = sum_h [m_h/(m_h-1)] sum_j (T_hj - mean_h(T))(T_hj - mean_h(T))^T`.
The covariance unit is fraction squared; probabilities remain fractions.
Retain all positive-weight design rows, including zero-domain PSUs. Use no
finite-population correction, consistent with the existing scalar estimator.
Fail on a singleton full-design stratum; an empty domain has unavailable
estimates/covariance rather than a fabricated zero.

Stack complete and partial partitions and all registered domains in one vector
so cross-definition and cross-domain dependence is retained. Partial lower and
upper membership endpoints are fixed sums of the disjoint subset coordinates:
lower includes its singleton; upper includes every subset containing that label.
Propagate their joint covariance through `A V A^T`. Missing-category ranges and
sampling covariance of their endpoints remain distinct. Do not select one
point inside a range, introduce independent draws or claim simultaneous bounds.

Partition closure and limited PSU support make singularity expected. Preserve
the matrix; no ridge, eigenvalue clipping, pseudo-inverse, rescaling or fitted
distribution is introduced. Numerical diagnostics describe symmetry, closure
and positive-semidefiniteness; they are not clinical acceptance thresholds.
This covers sampling uncertainty only, excluding measurement error, missingness
bias, latent-state definition, temporal/geographic transport and structural
uncertainty. Normal laboratory values are not general metabolic health, and
diabetes of any type is not verified T2D.

Primary method sources:

- [CDC variance tutorial](https://wwwn.cdc.gov/nchs/nhanes/tutorials/varianceestimation.aspx),
  Taylor Linearization, Analyzing Subgroups, Degrees of Freedom: masked design,
  full positive-weight sample and domain support.
- [Official survey package manual](https://stat.ethz.ch/CRAN/web/packages/survey/refman/survey.html#svyCprod),
  Computations for survey variances: cluster sums, stratum centering, corrected
  outer products. This is a documented Python implementation, not a claim that
  R executed the results. Full method documents remain optional fetch-only.

## Verification before interpretation

Check independently hand-calculated negative complement covariance; existing
scalar diagonal and point equality; scale invariance; zero-domain PSU retention;
symmetry/PSD and partition null directions; overlapping-domain dependence;
projected-bound equality to direct binary estimates; empty-domain and malformed
design rejection. Reproduce offline against pinned source bytes. Verify old
category estimates, bounds and standard errors are unchanged.

Preserve all active parameters, equations, scenarios, five scientific blockers
and canonical baseline/UPF/PreChronic numerical outputs. Refresh the two active
observation reports only in their evidence-registry provenance hash if needed;
preserve historical protocols and receipts. Run full tests, Ruff and tracked
source/package checks. A research-backed assessment can support this survey
calculation without claiming clinical initialization or independent validation.
