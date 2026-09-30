# Preserving DPP observations before fitting a clinical model

The DPP adapter design advances the observation layer required by
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58). Its job is to preserve what a
source records, with its units, history and missing information. It does not
classify glycemia, infer a biological state, estimate a transition or activate a
dietary effect. Current fixtures are synthetic software examples only.

The [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) separates
measurements, diagnosis history, observation times and latent model states. DPP
offers useful documentation for that separation. Normal measured glucose is not
general metabolic health, and a lower later value does not erase a diagnosis or
establish remission.

## Public documentation and request-only records

The primary sources are the
[original DPP report](https://doi.org/10.1056/NEJMoa012512), its
[public primary manuscript](https://pmc.ncbi.nlm.nih.gov/articles/PMC1370926/),
the [original study protocol](https://dppos.bsc.gwu.edu/documents/1124073/1127212/DPPPROTOCOL.PDF/807eddd1-d9bf-497d-89f0-5de15fc43d79),
and the
[February 2008 release documentation](https://repository.niddk.nih.gov/media/studies/dpp/Documents/Documentation%20for%20full%20scale%20DPP%20data%20release.pdf).
Page references below are the physical pages of that release document, whose
printed page numbers agree with the physical pages.

The [current NIDDK catalog](https://repository.niddk.nih.gov/study/38) identifies
DPP Version 9, updated June 20, 2024, DOI
[10.58020/3hw5-cf91](https://doi.org/10.58020/3hw5-cf91), as available for request.
Public protocol, forms, codebooks and the
[archive roadmap](https://repository.niddk.nih.gov/public/study_document/DPP_V9/DPP_Roadmap_V9.pdf)
are not an unrestricted participant-data download. The older documentation's
phrase "public release" must not be read as present access authorization. No
records have been requested, downloaded or inspected for this adapter design.
Access, permitted use and redistribution require separate review before intake.

The original report stops at March 31, 2001. The documented release stops at
July 31, 2001, includes the discontinued troglitazone arm and only clinics that
approved release. Its de-identification removes calendar dates and centers and
coarsens demographic and baseline measurements. The public Version 4.5 protocol
is dated November 6, 2001 and includes later bridge/washout provisions. These
sources cannot silently substitute for one another. See report Methods,
Statistical Analysis and Early Closure; release pages 4–6; protocol cover and
modification history.

The trial enrolled a selected population with elevated fasting glucose and
impaired glucose tolerance, under criteria that changed during recruitment.
The released baseline fasting-glucose field also recodes some original values
(release page 6). A source code must not become an exact assay measurement or a
latent metabolic state merely because it is numeric. Eligibility and recoding
need a separate reviewed mapping before any clinical use.

## The clocks and fields have different jobs

The EVENTS dictionary on pages 25–26 and common-variable definitions on page 11
give the following meanings. Preserve the source value alongside the typed
meaning; missing status must remain unknown.

| Source field | Documented unit or type | Meaning to preserve | What it does not establish |
| --- | --- | --- | --- |
| `DIABF` | Source diagnosis indicator | Whether diabetes was diagnosed during DPP follow-up | Current glycemia, lifetime diagnosis history, diabetes type or a latent engine state |
| `DIABT` | Years from randomization | Diagnosis-visit time for a source case; last glucose-assessment time for a source noncase | Exact biological onset, a verified trigger/confirmation date, or days under a guessed conversion |
| `DIABV` | Grouped interval code | Diagnosis interval for a case; final glucose-assessment interval for a noncase | Elapsed years, the nominal `VISIT` label, or a measured negative state throughout an interval |
| `TOTALTIM` | Years from randomization | Time through the last visit of any type at the release's data lock | Last glucose assessment, independently verified last contact or diabetes-free follow-up time |
| `DAYSRAND` | Days relative to randomization | Actual timing of the particular recorded visit; screening/run-in values can be negative | A calendar date, a scheduled target date, or diabetes-onset time |
| `DEATHDAYS` | Days relative to randomization | Time to recorded death; documented as missing for participants alive at the end | A zero death time when absent, an independently verified censoring reason, or comparable source years without a conversion contract |

`DEATH` is a separate source death indicator. Preserve its relationship with
`DEATHDAYS`; an unknown indicator cannot become "alive" because its time is
missing. A time reported with unknown diagnosis status should likewise remain a
source time of unresolved event/censoring meaning. Neither missing times nor
missing indicators may be silently replaced with zero.

For a participant without a source diabetes diagnosis, a final glucose test and
a later visit can be different events. The adapter therefore retains both
`DIABT` and `TOTALTIM`. It must not extend glucose observation to the later
visit. Last contact is a separate quantity and remains unknown unless an
explicit observation supports it. Similarly, a visit's negative `DAYSRAND`
value can correctly represent screening before randomization; it is not
automatically an invalid record.

## Preserve grouped detection and confirmation separately

Release page 8 describes grouped diagnosis windows and a discrete-tie analysis.
An out-of-window visit can retain its nominal annual `VISIT` label while the
diagnosis belongs to the window when the measurements were actually taken.
Page 25 gives the first interval a special start at randomization. Preserve the
reported interval code; do not generate uniform intervals, equate it to the
visit label, or invent an exact onset from its midpoint. Even boundary inclusion
and converting calendar-month windows to days need a verified convention.

The original report's Outcome Measures and release page 8 require repeat
confirmation. The release distinguishes `CON`, a visit to confirm **or not
confirm** diabetes, from `POV`, a visit after glucose confirmation (page 11).
A `CON` label alone is not a positive result. A single elevated measurement is
not a confirmed source event, and the two different glucose assays need not be
treated as interchangeable observations.

The LAB description says it includes regularly scheduled laboratory data, while
its measurement table explicitly includes confirmation measurements (pages
16–17). That table documents possible coverage; it does not prove every
confirmation, symptomatic test or missed visit is present in a future authorized
package. Keep assay values, visit roles and missing-test information separate
from the source's created diagnosis indicator. Do not reconstruct the indicator
with a newly invented threshold algorithm.

## Units are known; conversions and ordering are not

The dictionary establishes days for visit/death times and years for the two
follow-up summaries. It does not establish a day-to-year denominator, rounding
rule or exact choice of trigger versus confirmation timing for `DIABT`.
Preserving a value with its native unit is therefore stronger than prematurely
"normalizing" all fields into days.

An adapter may check structural types, finite numbers, recognized units and
consistent source identity. It must not compare a source-year endpoint directly
with a source-day death, choose a competing-event order, or enforce an equality
between the two clocks until conversion and event-dating rules are verified.
Even after a conversion is supported, recorded detection and biological onset
remain different quantities.

Calendar dates are absent and randomization periods are grouped. They do not
establish exact original-report cutoff dates for each participant. Historical
diagnostic rules also changed during the study. This adapter preserves those
source limitations and does not extract, register or apply clinical thresholds.

## Preservation contract and synthetic checks

Keep source summaries and visit observations as separate typed objects linked by
a local participant key. The batch records source/release identity; the frozen
[field contract](validation/dpp-observation-contract-v1.json) records the original
field names and their meaning. Typed objects retain native units, missingness and
observation roles; the aggregate audit exposes unresolved semantics. Assignment,
measurements and diagnosis history must remain separate. A later model-ready
transform requires its own reviewed mapping and evidence.

The current DPP command uses a synthetic fixture exercising preservation and
rejection of unsupported interpretations. The library validates explicitly
normalized objects; valid column names and types do not certify source access,
an importer or a clinical model. It does not load SAS records. Participant
histories must not be exported into the public repository. Useful checks include:

- Retain separate last-glucose and last-contact times, including when they differ.
- Preserve negative screening times, unknown status and missing assays.
- Retain `DIABV` independently of the visit label; do not infer an onset midpoint.
- Keep source diagnosis history after a later lower glucose value; do not infer
  recovery, remission or type 2 diabetes.
- Keep confirmation-visit role distinct from positive confirmation.
- Reject silent conversion or cross-unit event ordering, and reject an attempt
  to obtain clinical likelihood inputs from preservation-only objects.
- Leave fixtures labeled synthetic and confirm that model inputs and canonical
  scenario results are unchanged.

These are structural software checks, not a clinical acceptance tolerance or
evidence that the synthetic histories occur in DPP.

## Library objects and the local demonstration

The adapter lives in
[clinical_observations.py](../src/demeter/data/clinical_observations.py).
`preserve_observations(payload)` returns an `ObservationBatch` after strict
structural validation. `summarize_observations(batch)` returns aggregate counts,
unknowns, definite same-unit contradictions and fit blockers. It does not emit
participant identifiers or individual measurements.

The main objects make the distinctions visible:

| Object | Preserved information |
| --- | --- |
| `RelativeDayTime` | Explicit exact day, interval bounds or unknown time, relative to randomization; negative screening days are allowed |
| `SourceEventsSummary` | Follow-up diagnosis, separate prior history/type, native source-year endpoint and last-visit summaries, grouped visit code and death |
| `GlucoseObservation` | Assay, value or missing/unknown status, supplied unit and unit status, collection time and visit purpose |
| `DiagnosisObservation` | Supplied confirmed/not-confirmed/unknown outcome, separate first-positive and confirmation times, source definition and test references |
| `TreatmentChange` | Supplied treatment action and time, with unknown history retained |
| `FollowUp` | Separate last glucose and last contact times plus supplied censoring reason |

In `SourceEventsSummary`, `source_glucose_endpoint_years` preserves `DIABT`,
`source_visit_group` preserves `DIABV`, and `source_last_visit_years` preserves
`TOTALTIM`. These year values do not populate any `RelativeDayTime`. The death
time is supplied separately in relative days. Confirmation times are not
invented from a `CON` label or derived by thresholding glucose.

Prior diagnosis remains separate from diagnosis during source follow-up. The
current diagnosis object does not establish that an observation belongs within
the source's follow-up window. A confirmed observation alongside a negative
follow-up diagnosis indicator is therefore a scope question to resolve, rather
than automatic evidence of a contradiction or a new diagnosis.

After completing the repository's [setup instructions](../README.md), run the
following from the repository root. This command performs no source download or
participant-data request:

```powershell
uv run demeter evidence dpp-observations --output outputs/dpp-observations.json
Get-Content outputs/dpp-observations.json
```

On macOS or Linux:

```bash
uv run demeter evidence dpp-observations --output outputs/dpp-observations.json
cat outputs/dpp-observations.json
```

The JSON is a validation-only audit of registered synthetic examples. A later
lower value leaves diagnosis history intact; a confirmation visit alone does
not create a diagnosis; absent tests stay missing or unknown; different glucose
and contact times stay different. The audit also keeps source years and grouped
visit codes unresolved. These examples demonstrate software behavior, not DPP
participant outcomes or the success of an intervention.

If the four pinned public documents have already been cached under
`outputs/dpp-appraisal`, optionally verify their unchanged bytes as well:

```bash
uv run demeter evidence dpp-observations --raw outputs/dpp-appraisal --output outputs/dpp-observations.json
```

The optional directory contains `primary-report.html`,
`dpp-protocol-v4.5.pdf`, `niddk-full-scale-release-documentation.pdf` and
`niddk-study-38.html`. The command checks their SHA-256 pins against the
[source receipts](validation/dpp-documentation-source-receipts.json). It does
not interpret the full documents, refresh them from the network or inspect
records. Full-content caches remain ignored local inspection artifacts; only
small provenance receipts and the contract belong in the repository. An absent
or changed document is a verification problem, not permission to replace the
pinned bytes or treat a newer source as equivalent.

## What must be resolved before a clinical fit

The adapter supplies neither a likelihood nor fitted hazards. Before proposing
one, verify an authorized package's actual field coverage and resolve the
following blockers:

- Source version, release selection, rights and original-report versus release
  horizons.
- Baseline/history/type mapping, de-identification and historical diagnostic
  algorithm, with any clinical definitions registered separately before use.
- Assay conditions, first trigger, repeat confirmation, missed tests,
  interval boundaries, native-year conversion and event/censoring semantics.
- Competing death, last glucose, last contact, withdrawal/loss and informative
  observation timing.
- Assignment, actual exposure, adherence, treatment changes and phase-specific
  intervention packages.
- An estimable observation/transition likelihood, joint uncertainty and an
  evaluation partition frozen before reserved-record inspection.

DPP's lifestyle package combines diet, weight-loss goals, activity and behavioral
support; it does not identify an isolated food or UPF effect. First-diabetes
comparisons alone do not separate competing progression and recovery hazards.
The protocol's planned death-composite and recurrent-event analyses are not
proof that the original report fitted those clinical processes. See original
report Interventions and Statistical Analysis, and protocol section 10.3.

The smallest next deliverable is a coverage matrix for the public forms and
codebooks: for each required baseline, trigger, confirmation, missed-test,
treatment, exposure and death observation, record the exact source field and
primary locator or explicitly mark it unavailable. Keep documented availability
separate from actual coverage in an authorized package. The matrix should resolve
whether a proposed observation likelihood has the information it needs before
any clinical fit is attempted. For #58 it must also show whether measured dietary
exposure can be separated from the lifestyle package; an assigned lifestyle arm
alone cannot supply that distinction.

This is source-informed software work after public results and documentation
were inspected, not preregistration or independent clinical validation. #57,
#58, clinical fitting and scientific engine activation remain unresolved.
Codex-assisted critique for the Food is Health-affiliated project does not
replace external human scientific review.
