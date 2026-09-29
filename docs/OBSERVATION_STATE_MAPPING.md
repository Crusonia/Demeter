# From survey observations to model states

Demeter now reports how its existing NHANES categories relate to the engine's
health stocks, with missing observations retained in the denominator. The
crosswalk identifies unresolved substitutions; it does not initialize the engine
or establish clinical states. Issue [#56](https://github.com/Crusonia/Demeter/issues/56)
remains open for evidence-supported initialization.

Run from the repository on Windows, macOS or Linux:

```text
uv run demeter evidence state-mapping --output outputs/state-mapping.json
```

This reads the ten already archived public-use files offline and exports only
aggregates. The [saved report](validation/issue-56-state-mapping.json) carries
the source, implementation and registry hashes, definitions, all age/sex domains
and the crosswalk. [RFC-56](rfcs/RFC-56-observation-state-mapping.md) records the
method and alternatives. No source file or original classifier is changed.

## What the categories can tell us

| Survey observation | Candidate engine label | Why direct initialization remains unresolved |
| --- | --- | --- |
| Normoglycemia | Legacy `healthy` | Normal glycemia does not establish general metabolic health or exclude other disease. |
| Prediabetes | Legacy `ir` | A glycemic threshold category is not all insulin resistance. |
| Diabetes of any type | `t2d` | Diabetes type is not identified; no assumed T2D fraction is subtracted or invented. |
| Lower measured risk | Four-state `healthy` | The selected markers and diagnosis list do not establish overall health. |
| PreChronic candidate | `prechronic` | A candidate marker-count rule is not an established clinical diagnosis or nationally transported stock. |
| Prediabetes | Four-state `prediabetes` | The observation label aligns, but missingness, age detail and target-period transport remain unresolved. |
| Other reported diagnosis | No matching stock | These people cannot be dropped or allocated to healthy by default. |
| Unclassified | No known state | Missing measurements/interviews remain unknown. |

The two PreChronic definitions require normoglycemia and exclude the listed
diagnoses. They therefore cannot overlap with glycemic prediabetes by definition.
This does not mean non-glycemic risk factors are absent from people with
prediabetes; higher-priority categories take precedence. `risk_1` and `risk_2`
are alternative rules for the same people, not additive populations.

## Coverage and the denominator

Among 15,560 source records, 4,476 have positive fasting-subsample weights. The
existing adult and known-pregnancy rules leave 3,769 eligible records. The
[glycemic reconstruction](NHANES_PREVALENCE.md) classifies 3,757; the richer
[PreChronic reconstruction](PRECHRONIC.md) classifies 3,211 under either rule.

| Existing definition | Classified records | Unclassified records | Unclassified share of eligible survey weight, with 95% interval |
| --- | ---: | ---: | --- |
| Glycemic | 3,757 | 12 | 0.37% (0.15–0.89%) |
| PreChronic `risk_1` or `risk_2` | 3,211 | 558 | 12.06% (9.62–15.02%) |

The PreChronic remainder comprises 12 incomplete glycemic observations and 546
records missing another required marker or diagnosis response. Both alternatives
have the same complete-case requirement. These missing shares are data-coverage
diagnostics, not disease prevalence or evidence that the unknown people are healthy.

For an eligible age/sex domain, every category's proportion uses **all eligible
weight**, including unclassified records. Categories plus the unclassified share
sum to one. The earlier benchmark bundles report prevalence among complete cases;
both are useful, but their denominators must not be confused. The new tests
reconcile the two calculations without modifying either benchmark.

The survey intervals use the existing Taylor logit-t method with full survey
design retained. They quantify marginal sampling uncertainty only. Missing-data
bias, diagnostic error, definition choice, national transport and full NCHS
reliability screening remain outside them. Categories share respondents; these
are not independent distributions for model initialization. Empty and boundary
intervals remain explicitly unavailable. Overlapping age domains cannot be summed.

## Known diagnoses and age coverage

The report identifies 130 eligible people reporting diabetes whose measurements
are below both diabetes thresholds. Within complete cases, prior diagnosis retains
priority. Their low measurements do not establish recovery or remission.

The existing complete-case rule leaves one reported-diabetes record unclassified
in the glycemic benchmark and 120 in the richer PreChronic benchmark. The new
report exposes that limitation. It does not erase a known diagnosis or imply that
the classification captures every diagnosable case. A future diagnosis-first
partial-observation method needs an explicit definition, missing-data appraisal
and comparison with the preserved original benchmarks. Medication use and duration
of control are not established by the currently ingested fields.

There are 236 eligible records in the public age top-code. The
[P_DEMO codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DEMO.htm)
defines that code as age 80 or older. They contribute to the existing aggregate
adult estimates; the report does not fabricate their individual ages. The source
also limits public pregnancy status to a narrower age window. Pediatric disease,
single-year oldest-age shares, institutionalized populations and transport from
2017–March 2020 to the engine's baseline year remain unresolved.

## Evidence change and verification

`datasets.observation_state_mapping` is derived, grade C and benchmark-only.
The new age top-code metadata cites the official codebook. All clinical cutoffs,
survey weights, confidence levels and candidate rules are the existing registry
definitions. No active parameter value, uncertainty distribution or health
equation changes. The [before/after receipt](validation/issue-56-state-mapping-before-after.json)
shows identical numerical outputs for baseline, UPF reduction and PreChronic
baseline; only evidence provenance hashes differ.

Focused checks cover a hand-calculated weighted partition, missingness accounting,
known diagnosis below laboratory thresholds, alternative definitions, age coding,
rejection of direct initialization, offline source reload and all age/sex
comparisons with the prior benchmark bundles. This verifies observation accounting,
not the validity of a latent-state measurement model.

Author/date: Codex-assisted analysis for the Food is Health-affiliated project,
September 29, 2026 (UTC). External expert review and maintainer disposition remain
pending; independent human review is not claimed. Type-specific classification,
partial-observation handling, age/vintage transport and evidence-supported engine
initialization still require work. Missing evidence remains an explicit gap.
