# Evidence and learning work after Explorer

Implementation tracking for the maintainer's requested next steps, September 29,
2026. This preserves the full scientific objective; a completed software feature
does not satisfy an unresolved empirical requirement.

| Work | Tracking | Completion evidence |
| --- | --- | --- |
| Independent mortality prediction | [#55](https://github.com/Crusonia/Demeter/issues/55) | Frozen models/protocol, untouched-cycle evaluation, uncertainty, source receipts and a scoped assessment |
| Observation-to-state mapping | [#56](https://github.com/Crusonia/Demeter/issues/56) | Explicit definitions, age/sex coverage, unclassified remainder and evidence-supported initialization |
| Progression and reversal | [#57](https://github.com/Crusonia/Demeter/issues/57) | Identifiable longitudinal likelihood, compatible evidence, joint uncertainty and independent checks |
| One food-to-health pathway | [#58](https://github.com/Crusonia/Demeter/issues/58) | Matched exposure/dose/endpoint/lag, causal appraisal, reproducible estimates and appropriate validation |
| Explorer evidence explanations | [#59](https://github.com/Crusonia/Demeter/issues/59) | Chart/mechanism-specific sources, uncertainty and guided exercises verified in the browser and offline exports |

The first [mortality prediction evaluation](MORTALITY_VALIDATION.md) is implemented
in [PR #60](https://github.com/Crusonia/Demeter/pull/60). It retains inconclusive
comparisons and does not close the remaining health-model acceptance gates.
The assessment also records a post-intake source-guard correction without
rewriting the original protocol or numerical result.

Issue #1 was reopened to match its scientific acceptance state. These tasks feed
[milestone #27](https://github.com/Crusonia/Demeter/issues/27); none automatically
authorizes a scientific release. Each missing value or unidentifiable relationship
remains visible until evidence resolves it. The mortality prediction benchmark is
not a substitute for state transitions, dietary causality or national transport.

After the health foundations meet their acceptance criteria, the next upstream
and downstream implementation priorities are [prices and substitution (#11)](https://github.com/Crusonia/Demeter/issues/11)
and [utilization/provider economics (#10)](https://github.com/Crusonia/Demeter/issues/10).
Their requirements remain in the existing roadmap. The local Explorer is separate
from the [future public Simulator (#20)](https://github.com/Crusonia/Demeter/issues/20).

## Integrated foundation and public evidence route

[PR #63](https://github.com/Crusonia/Demeter/pull/63) combines the mortality
evaluation from #60, observation mapping from #61, Explorer explanations from
#62, and the longitudinal/food-pathway work. It provides one integration target
for maintainer review; the individual PRs retain their development history.
It was merged to `main` on September 29, 2026 as `94031c3`. Scientific acceptance
remains separate from that completed software integration.

Shared registry and package-manifest conflicts are resolved by preserving each
branch's evidence definitions and artifact entries. The two observation reports
are rebuilt against the combined registry: only their evidence-registry hash
changes, with all observations, estimates, intervals, source receipts and
implementation hashes retained. Original mortality protocols, amendments and
intake receipts remain unchanged. Package checks cover the combined inventory.

The maintainer selected [public sources](PUBLIC_EVIDENCE_ROADMAP.md) as the next
route. The executable Chen cohort intake reproduces cohort/event totals while
retaining a follow-up discrepancy; it does not fit or activate rates. The
[timing audit](CHEN_TIMING_AUDIT.md) now checks duration totals, mean/median,
calendar bounds and publication-rate arithmetic. It keeps Chen as a descriptive
benchmark while compatible observations are sought. Institutional
access is optional. The [source appraisal and access brief](LONGITUDINAL_SOURCE_APPRAISAL.md)
preserve alternative routes. The integration does not provide national
state initialization, identified progression/reversal hazards or an active
food-to-disease effect. Those requirements keep #1, #57, #58 and milestone #27
open; the bounded #56 software work is complete, with scientific state
initialization still unresolved. Synthetic dietary trajectories remain validation-only.

The [Reus pathway assessment](REUS_DIABETES_PATHWAY.md) adds corrected
first-diabetes trial benchmarks and executable synthetic tests of the current
annual transition and dietary-response operators. All six reported overall
contrasts are retained; original/corrected analyses and shared arms are dependent.
This advances #58's source and equation assessment. It does not identify separate
progression/recovery effects, a consumed UPF dose, response lag or national causal
transport. Its [before/after receipt](validation/issue-58-reus-before-after.json)
records unchanged canonical numerical outputs and active parameters.

The [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) now specifies
the required baseline categories, repeat testing and confirmation, event dating,
exposure, visit timing, treatment, missingness, death and loss. The executable
[DPP observation adapter](DPP_OBSERVATION_ADAPTER.md) now preserves explicit
normalized observations and exports a synthetic aggregate audit. It retains
source-year summaries separately from relative-day visits, confirmation separately
from trigger tests, and last glucose separately from last contact. Four public
documentation receipts are pinned; participant records remain request-only and
have not been acquired. This is observation preservation, not a SAS importer,
clinical likelihood or transition fit. Its
[before/after receipt](validation/issue-57-dpp-before-after.json) records unchanged
active parameters and canonical numerical outputs.

The [DPP source-field coverage matrix](DPP_SOURCE_COVERAGE.md) now records
baseline/history, trigger/confirmation, missing tests, treatment, exposure and
competing-death documentation. Actual participant coverage remains not acquired.
Medication recall windows, excluded calendar dates and version discrepancies
are explicit; no source-year conversion or clinical fit is introduced. DPP's
lifestyle package is not an isolated dietary effect.

The [PREVIEW endpoint audit](PREVIEW_ENDPOINT_AUDIT.md) follows that source route
with published normal-glucose endpoint counts. Its frozen used-source protocol
separates available-endpoint descriptions, published adjusted effects, and
deterministic missing-label completions. Source conflicts and unknown death,
treatment, diagnosis history and repeated-year dependence remain explicit. It
does not identify individual reversal, annual transition hazards, a consumed UPF
dose, or a lag, and does not activate any engine parameter.

The [TOTUM63 source-row adequacy audit](TOTUM_SOURCE_ADEQUACY.md) checks the public
baseline/follow-up glucose surface before accepting a likelihood. The
[design extension](rfcs/RFC-57-58-totum-source-adequacy.md) preserves record identity,
measurement, missingness and stopping requirements. Coverage counts cannot certify
unique people, valid assays or a full randomized cohort. No clinical rate or
food-to-health effect is fitted or activated.

The [Whitehall II endpoint package](WHITEHALL_ENDPOINT.md) now makes one narrow
conditional binomial observation likelihood executable. Its endpoint probability
and interval depend on declared working assumptions; those assumptions are not
established by the source. A descriptive-only mode makes that boundary visible.
No annual clinical transitions, dietary response or national parameters are fitted.

The [paired remission observation model](PAIRED_REMISSION_OBSERVATIONS.md) now
preserves same-person positive-label information across DiRECT visits. It reports
integer feasible tables and unresolved assessment/death partitions, retaining
marginal-only and conditional subgroup constraints. A literal denominator conflict
and failed XML selection remain recorded; the current selection uses separately
published cohort/remission counts under an explicit common-ITT assumption.
This adds a temporal observation capability without identifying clinical hazards,
latent remission/relapse or an isolated dietary effect. Canonical numerical health
outputs and active parameters remain unchanged; #57/#58/#1/#27 stay open.

The [linked-path likelihood evaluator](LONGITUDINAL_LIKELIHOOD.md) now supplies the
missing mathematical software layer for declared panel, first-entry, competing-
death and censoring observations. Frozen synthetic identities and local rank
diagnostics verify the implementation; no participant importer, empirical fit,
joint clinical uncertainty or engine activation is included. Source compatibility
and scientific acceptance remain separate gates.

Next, prioritize a compatible unrestricted longitudinal package or sufficient
published observations for an identified progression/reversal likelihood. Further
blank-form inspection cannot replace participant histories. Resolve timing,
source selection, observation/censoring assumptions and likelihood identification;
freeze joint-uncertainty and evaluation plans before fitting. Keep national
transport and unidentified causal parameters unresolved. The full requirements
of #57, #58, #1 and milestone #27 remain open.
