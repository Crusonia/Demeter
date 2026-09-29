# Preserving known categories when observations are incomplete

The optional partial-observation method advances
[#56](https://github.com/Crusonia/Demeter/issues/56) by retaining information that
the complete-case benchmark cannot use. A reported diabetes diagnosis should not
disappear because a waist measurement or laboratory result is absent. When the
available observations do not determine one category, Demeter retains the set of
possible categories and reports its implications for population proportions.

This is an observation method, not a national health-state initializer. The
[proposed RFC extension](rfcs/RFC-56-observation-state-mapping.md#proposed-extension-partial-observations-september-29-2026)
was committed in `bf33ca0` before implementation, after the existing data and
complete-case audit had been inspected. It is not preregistration or a holdout.

## Run and compare

After [installation](GETTING_STARTED.md), the same commands work in Windows
PowerShell, macOS and Linux:

```text
uv run demeter evidence state-mapping --output outputs/complete-case-mapping.json
uv run demeter evidence state-mapping --partial --output outputs/partial-observations.json
```

Both commands use the same ten checksummed, archived public-use files offline.
They export aggregates only. The [complete-case report](OBSERVATION_STATE_MAPPING.md)
and original published-table comparisons remain available; `--partial` explicitly
selects the alternative method. The
[saved result](validation/issue-56-partial-observations.json) includes every
registered age/sex domain, category-set partition, bound endpoints, sampling
intervals, definitions, source receipts and implementation hashes.

## What the observations now establish

Of 3,769 eligible positive-weight adult records:

| Observation definition | Complete cases | Resolved using partial observations | Newly resolved | Still unresolved | Unresolved share of eligible survey weight |
| --- | ---: | ---: | ---: | ---: | ---: |
| Glycemic | 3,757 | 3,758 | 1 | 11 | 0.36% |
| PreChronic candidate `risk_1` | 3,211 | 3,706 | 495 | 63 | 1.57% |
| PreChronic candidate `risk_2` | 3,211 | 3,717 | 506 | 52 | 1.86% |

Every original complete-case category is preserved. No eligible respondent with a
reported diabetes diagnosis remains unresolved under any of the three methods.
The two candidate definitions are alternatives applied to the same people. Their
counts and percentages must not be added. Different survey weights also mean a
smaller unresolved record count can have a larger unresolved weighted share.

These improvements reflect classification with less missing information, not
health improvement, diagnostic confirmation, evidence of T2D, or validation of
PreChronic as a clinical state.

## How incomplete information is represented

The registered category priority remains diabetes, prediabetes, another listed
reported diagnosis, earlier-risk candidate, then lower measured risk. A known
higher-priority category does not require unrelated lower-priority observations.

A valid measured glycemic value above the registered diabetes threshold is enough
to establish the survey's any-type diabetes category. A low value cannot exclude
a higher category if another required observation is unknown. Refused, unknown,
absent or otherwise unrecognized interview responses remain unknown. Invalid
nonfinite or nonpositive measurements likewise supply no category information.
The [CDC questionnaire codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DIQ.htm)
distinguishes yes, no and borderline responses from refusal and unknown responses;
the existing borderline handling is preserved.

An unknown diabetes response with two normal laboratory measurements leaves
normal glycemia and any-type diabetes possible. It does not, by itself, make
prediabetes possible. Category sets may therefore have gaps; they are not an
ordinal range with every intermediate state filled in.

The risk candidates use the existing waist, HDL, triglyceride and blood-pressure
rules. Missing markers may be positive or negative; the possible marker count
and known diagnoses determine the remaining categories. The blood-pressure marker
is deliberately coarsened to unknown unless all six original readings are valid.
Demeter does not silently average fewer readings. Because some partial readings
could themselves constrain that marker, the resulting bounds are conservative,
not necessarily the narrowest possible bounds over raw-value completions.

## Reading the bounds

For category C, `compatible_weight_range.lower` is the proportion of all eligible
survey weight definitely in C. The upper endpoint includes everyone whose
category set permits C. The `category_set_partition` preserves which categories
share the unresolved respondents, so separate upper bounds cannot be treated as
a jointly feasible population allocation.

For example, a synthetic group with 10% definitely in lower measured risk and 20%
possibly in either lower measured risk or another diagnosis has a 10%–30% range
for lower measured risk. The unresolved people have not been allocated or
imputed. Resolving their diagnosis response could narrow that range.

`endpoint_sampling` provides a separate Taylor logit-t survey interval for each
endpoint. The compatible-category range is not a confidence interval; the
endpoint intervals are not a simultaneous confidence region for the whole set.
They are not independent probability distributions for engine initialization.
No missing-at-random assumption is introduced. Survey selection, diagnostic
error, unmeasured diseases, diabetes type and transport remain unresolved.

## Model effect and verification

The registered `observation_partial_mapping` dataset is derived, grade C and
benchmark-only. No active parameter or engine equation changes. The
[before/after receipt](validation/issue-56-partial-before-after.json) compares
complete baseline, UPF-reduction and PreChronic simulation results: only their
two evidence-registry hashes differ. Raw source files and the old classifiers
are unchanged.

Checks compare category sets with independently enumerated completions, preserve
all complete cases, exercise diagnosis priority and threshold boundaries, verify
weighted bounds against hand arithmetic, conserve the category-set partition,
and confirm that additional observations only narrow possible categories. The
CLI must reproduce the exact canonical UTF-8/LF artifact on every platform.

Scientific scope: this resolves part of the missing-observation problem in #56.
Supported national initialization still needs type-specific classification,
age detail, population/vintage transport and joint uncertainty. External expert
review and maintainer disposition remain pending. Codex-assisted work for the
Food is Health-affiliated project, September 29, 2026 (UTC).
