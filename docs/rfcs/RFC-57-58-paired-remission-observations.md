# RFC-57/58: Preserve paired remission observations and unknown follow-up

Status: proposed source-specific observation model; October 1, 2026 UTC.
Supports [#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58), without closing their full
clinical requirements. External expert review and scientific use remain pending.

## Problem and supported target

Repeated remission reports contain information about the same people. Treating
them as independent marginal observations discards that history. Conversely,
calling an unavailable primary endpoint a measured relapse invents a transition.
Preserve prior diagnosed T2D, source-positive snapshots, assessed nonremission,
unassessed outcomes and possible competing death separately.

Use the overlapping DiRECT [one-year accepted report](https://eprints.gla.ac.uk/153078/13/153078.pdf)
and [two-year accepted report](https://eprints.gla.ac.uk/180894/13/180894.pdf).
The latter's post-hoc weight analysis identifies a subgroup maintaining remission
between visits; its completeness as the full positive-positive cell is not stated.
The analysis must retain a marginal-only feasible set and a separately conditional
set using that subgroup as a lower bound. Source-coded failures cannot establish
assessed clinical relapse. The selected reports are one trial, not independent
replications, and the remission-conditioned comparison is not randomized.

The [frozen protocol](../validation/direct-paired-observations-protocol-v1.json)
selects literal counts and crosschecks before planned capture/calculation. Earlier
abstract outcomes and masked source context were already inspected: this is used
source work, not preregistration or independent evaluation. Both full publications
remain immutable, ignored and fetch-only. No participant package or access request
is involved; the public report's application-only data-sharing route is not used.

## Exact constraint model

Let N be the common intervention intention-to-treat cohort count; a and b its
source-positive remission counts at the first and second nominal visits; and x
the unknown same-person positive-positive count. A compatible integer joint table
has cells x, a-x, b-x, N-a-b+x. Thus max(0,a+b-N) <= x <= min(a,b).
If the reported maintaining subgroup m belongs to that cohort and has its stated
paired-positive meaning, add x >= m. Do not assert x=m or infer another joint cell
from an independently rounded percentage.

Every feasible x yields a whole table conserving N. Marginal intervals for its
cells share x and cannot be independently allocated. Bounds are deterministic
source-information ranges, not confidence intervals. There is no iid, missing-at-
random, absence-of-death, continuous-remission or common exact-duration assumption.

Among first-visit positives, second-visit failures remain an unresolved partition
of assessed nonremission, unassessed/unknown criterion and death. Without a public
joint partition, none of those components has an observed positive lower bound.
A mathematical lower bound of zero is not an observation of zero events. Positive
source classifications are source observations, not validated latent physiology.
Normal glycemia and remission never erase diagnosed-T2D history.

## Capability and boundary

### Source version amendment

The planned intake failed: the accepted two-year manuscript prints a second-visit
remission fraction with denominator 129, while both reports' intention-to-treat
cohort definitions say 149 per group. The [original failed receipt](../validation/direct-paired-failed-intake-v1.json)
is retained unchanged. No paired table is accepted from that failed version alone.

The [version amendment](../validation/direct-paired-observations-amendment-v2.json)
selects literal counts from the published abstract in the
[NLM article record](https://pubmed.ncbi.nlm.nih.gov/30852132/), after verifying its
DOI, exact field and source identity. The amendment precedes planned extraction
of those new literal counts, after the original failed intake and earlier abstract
exposure. It requires explicit published denominator agreement with both cohort
definitions and numerator agreement with the accepted manuscript. Agreement with
a rounded percentage cannot repair this conflict. The accepted fraction and its
failed check remain visible beside any result from the amended published source.
This is a version preference, not an author-issued erratum; no such correction
was identified in the NLM relationship inventory. No version-of-record body is
claimed to have been acquired.

The v2 XML selection itself failed before count capture: the exact field label
is `FINDINGS`, and the abstract states the ITT cohort count separately from the
remission numerator. It does not print an endpoint-specific remission denominator.
The [retained locator failure](../validation/direct-paired-amendment-v2-failure.json)
and [v3 selection](../validation/direct-paired-observations-amendment-v3.json) make
that distinction explicit before the new integer capture. The resulting feasible
sets are conditional on those published counts referring to the same stated ITT
cohort, supported by the abstract context and the main primary-outcome methods.
That assumption is visible; participant-level cohort membership is not verified.
Neither source failure is silently repaired or removed.

Implement integer feasible-table constraints and source-linked paired-history
reporting, not an annual rate fit or an engine remission flow. This advances the
temporal observation layer of the [clinical contract](../CLINICAL_OBSERVATION_CONTRACT.md).
Fitting clinical hazards still needs compatible visit timing, assessment/history,
treatment, competing-event and selection evidence; dietary effects additionally
need a matched dose, lag and causal estimand. No UPF, national, mortality, healthspan
or healthcare-cost parameter is activated by this work.

Design chain: the health portion of Q-03/RM-04 → P-02 → I-01/I-07/I-11/I-12 →
F-08 → T-01/T-02/T-05/T-06/T-08 in the [design registers](../design/README.md).
L-00 supplies accounting only. Business externalities, value capture and economic
feedbacks are outside this v0.1 observation change.

## Validation and review

Check bounds against independently enumerated tiny joint tables, conserve counts
at both extremes, reject infeasible/source-inconsistent inputs, retain zero-
denominator unknowns and demonstrate that added paired information narrows the
set. Verify selected PDF cells visually and by independent source review. Preserve
failure receipts, protocol hashes and raw bytes; verify unchanged canonical
numerical outputs and run full software/package checks.

Authors: Codex-assisted work for the Food is Health-affiliated project. Software
assessment pending at the implementation commit; source/identification assessment
scoped to this observation target. Independent human scientific review pending.
Merge and scientific acceptance remain distinct. #57/#58/#1/#27 stay open.
