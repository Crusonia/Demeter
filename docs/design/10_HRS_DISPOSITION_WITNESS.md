# HRS synthetic observation and disposition witness

Status: proposed software contract, October 3, 2026. No participant intake,
source loader, empirical estimate, clinical likelihood or engine change.
This follows the [HRS checkpoint](../HRS_REPEAT_BIOMARKER_SOURCE_CHECKPOINT.md)
and I-01/I-05/I-07/I-11/I-12 -> F-08 -> T-01/T-02/T-05/T-08 in the
[design inventory](README.md). [RFC-56](../rfcs/RFC-56-observation-state-mapping.md),
the [clinical observation contract](../CLINICAL_OBSERVATION_CONTRACT.md) and
[current objective](../CODEX_V0_1_OBJECTIVE.md) retain their existing boundaries.

## What this checks

Every caller-declared synthetic baseline person remains represented when a
follow-up record is absent. Tracker disposition, diagnosis report, assay
selection/availability and specimen clock are orthogonal source facets.
Conservation is over people within each facet, never the sum of those facets.
No statistical distribution, missingness independence or temporal ordering is
assigned. This is a categorical reconciliation witness, not a patient simulator.

Existing `source_panel_reconstruction` and `followup_category_bounds` require
exhaustive outcome partitions or confirmed-death categories. They cannot be
applied to HRS report-based alive/deceased flags without changing their premises.
This witness therefore computes counts only, with no new bounds or likelihood.

## Verified documentary meanings

The [Tracker 2022 Final V1 PALIVE dictionary](https://hrs.isr.umich.edu/sites/default/files/meta/tracker/codebook/trk2022tr_r.htm)
describes 2016 codes: 1 alive at the wave; 2 presumed alive; 5 deceased at this
wave; 6 deceased as of a prior wave; blank not in this wave's sample. The alive
and deceased coding can rely on reports when vital status is uncertain. Presumed
alive can mean no current contact. These are tracker categories, not independently
validated clinical survival or mortality. A missing tracker row is different
from an observed blank PALIVE.

[2012 NC010](https://hrs.isr.umich.edu/sites/default/files/meta/2012/core/codebook/h12c_r.htm)
and [2016 PC010](https://hrs.isr.umich.edu/sites/default/files/meta/2016/core/codebook/h16c_r.htm)
concern reported diabetes or high blood sugar. Codes are 1 Yes, 3 dispute previous
record but now condition, 4 dispute previous record and no condition, 5 No,
8 unknown/not ascertained, 9 refused, and blank inapplicable/partial interview.
The prompt depends on new interview and prior recorded report: ever diagnosed,
carried prior record or since last interview. Code 1 alone does not distinguish
these universes. Disputes do not establish remission; No does not erase a prior
record; no code establishes diabetes type. The inspected codebooks also include
conditional diagnosis-year questions, but those fields are outside this witness.

These source meanings were read through ordinary public codebook display.
Original documentary HTTP requests returned 403, without reading bodies or
claiming producer hashes. The accompanying authored receipt will preserve those
failures, exact URLs/field locators and display-derived definitions. It is not
source admission or blinded preregistration; frequency tables were visible in
the used-source metadata before this software contract.

## Frozen input contract proposed for review

One library entry point is proposed:

```python
reconcile_dispositions(
    baseline_ids, tracker_records, diagnosis_records, assay_records,
    *, synthetic_only: bool,
)
```

Only an explicit Boolean `synthetic_only=True` is accepted. This is a caller
declaration, not proof that the inputs are synthetic and not authorization to
process empirical health records. No file/network
parser, automatic source cohort selection, default baseline population, source
wrapper or CLI is added. Inputs are copied into local validation state and are
never modified. Errors name only field/contract violations, not person keys.

Baseline IDs are caller-supplied, unique nonempty opaque strings without edge
whitespace. Leading zeros remain significant; numeric IDs are refused. They
have no presumed HRS HHID/PN format. Duplicate or orphan records are refused;
one tracker row per person and one diagnosis/assay row per person per nominal
wave are allowed. Duplicate rows are rejected even when values agree, rather
than selecting the last row.

Tracker records concern **2016 PALIVE only** and contain exactly `person_id` and
`palive`. These meanings are not silently extended to other waves. Allowed values are
Python integers 1, 2, 5, 6 or `None` for an **observed native blank**. Boolean values,
other numerics, strings and undocumented codes are refused. An absent row maps
to `no_tracker_observation`, preserving unknown follow-up.

Diagnosis records contain exactly `person_id`, `wave`, `response`, `universe`.
Wave is the literal string 2012 or 2016, identifying NC010 or PC010 only. Response
is a Python integer 1, 3, 4, 5, 8, 9 or `None` for an observed native blank. Universe is
explicitly supplied as `ever_prompt`, `prior_record_prompt`,
`since_last_interview_prompt` or `unknown`; it is never inferred from response.
The witness retains both facets without inventing source interview preloads or
cross-wave clinical history. It does not require source responses to be stable
across waves or convert reported No into an absence of past diagnosis.

Assay records contain exactly `person_id`, `wave`, `selected`, `availability`,
`clock`. They are **caller-defined synthetic facets**, not native HRS variables.
Selection is Boolean True/False or `None` for unknown. Availability is `available`,
`missing` or `unknown`; selected False with available is a contradictory supplied
selection claim and is refused. Availability has no concentration, threshold,
assay method or clinical-state meaning. Clock is `unknown` or `nominal_wave_only`.
No elapsed time, date or rate is accepted or derived. Missing source records
remain separate from all observed tokens. A deceased tracker code and available
assay do not conflict by themselves: specimen chronology is unknown.

## Output and checks

Return only fresh aggregate dictionaries: declared baseline count, tracker
category counts, diagnosis response/universe counts by nominal wave and assay
selection/availability/clock counts by nominal wave. Each marginal includes
missing-record tokens and sums to the declared baseline count. No people are
pooled across waves. Empty inputs produce zero counts and an explicitly empty
cohort, never a likelihood, risk estimate or evaluable empirical benchmark.

No IDs, individual rows, assay concentrations, joint trajectories or labelled
multiwave tables are returned. This software boundary does not authorize
processing empirical health rows; an empirical source wrapper would require a
separate used-source protocol, rights, source/code admission and disclosure rule.

Meaningful synthetic tests must cover absent follow-up, all native codes,
unknown/refused/blank distinctions, leading-zero identities, duplicated/orphan
keys, conflicting selection claims, death plus assay without invented order,
report changes without remission/type inference, untouched caller inputs,
empty cohorts and conservation in every orthogonal marginal. Reordering supplied
records must preserve the aggregate result; errors/output must not leak keys.

All five gates are false: `direct_initialization_allowed`, `clinical_fit_allowed`,
`engine_activation_allowed`, `sampling_distribution_assumed` and
`scientific_release_ready`. The result also declares source audit False, no
independent death ascertainment, no known specimen interval, no paired weights,
no fitted clinical parameters, and no national transport.

## Assessment

Software assessment: proposed contract; code and targeted verification pending.
Scientific assessment: automated documentary appraisal only; no clinical or
external expert acceptance. Missing specimen clocks, baseline-source selection
and complete ascertainment remain unresolved.
Merge disposition: pending maintainer review; this document changes no gate.
Scientific use: synthetic software validation only.
