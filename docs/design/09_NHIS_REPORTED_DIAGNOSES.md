# NHIS reported diagnoses as an observation benchmark

Status: used-source design and a synthetic software witness. No NHIS participant
file has been acquired or analyzed for this work. The proposed age/sex survey
benchmark is not implemented or admitted. The implemented categorical witness
has no source loader, survey estimator, clinical state mapping or engine entry.

This addresses the diagnosed component of the v0.1 age-specific T2D initializer
question. Its design chain is I-01/I-07/I-11/I-12 -> F-08 -> T-01/T-02/T-05/T-08
in the [input](04_MODEL_INPUTS.md) and
[formulation registers](05_FORMULATION_AND_TESTS.md), alongside
[RFC-56](../rfcs/RFC-56-observation-state-mapping.md) and the
[clinical observation contract](../CLINICAL_OBSERVATION_CONTRACT.md).
It supplies no dietary effect, mortality multiplier, transition rate or payer
cost. The [program vision](../PROJECT_VISION.md) and active v0.1 boundary apply.

## Question and source

How much of an age/sex survey domain's weighted population explicitly reports
having been told it has type 2 diabetes, and how much of the diagnosis/type
information remains unknown or inconsistent? This is a recorded-answer question.
Reported type is not independently confirmed clinical type. An ever-diagnosed
answer does not establish current disease activity or remission.

The official [2025 NHIS catalog](https://www.cdc.gov/nchs/nhis/documentation/2025-nhis.html)
advertises final public-use Sample Adult data and documentation. Its
[public codebook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2025/adult-codebook.pdf)
is dated July 29, 2026. The committed
[documentary receipts](../validation/nhis2025-typed-diagnosis-design-receipts-v1.json)
identify actual metadata bytes, retrieval times and selected PDF pages; they are
not participant-source admission. The official SAS input statements were read
as field documentation and were not executed.

| Field | Documented meaning | Codebook PDF page |
| --- | --- | --- |
| `DIBEV_A` | Ever told by a clinician that the respondent had diabetes; the question excludes gestational diabetes and prediabetes | 115 |
| `DIBTYPE_A` | Clinician's diabetes type as reported in the interview; its universe is `HHSTAT_A=1` and `DIBEV_A=1` | 124 |
| `AGEP_A` | Adult age; 85 denotes 85+, with distinct refused/not-ascertained/unknown codes | 21 |
| `SEX_A` | Reported Sample Adult sex, with distinct unknown-response codes | 19 |
| `PROXYFLAG_A` | Proxy used/not used, with distinct unknown-response codes | 12 |
| `WTFA_A` | Final annual Sample Adult survey weight | 4 |
| `PSTRAT`, `PPSU` | Annual public variance stratum and PSU | 7, 8 |

The current [NHANES DIQ_L codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DIQ_L.htm)
has no explicit diabetes-type question. Its diagnosis answer therefore cannot be
silently renamed T2D. Insulin use and diagnosis age must not manufacture a type.
NHIS and NHANES are different surveys and vintages: their individual files cannot
be joined into a common clinical cohort, and subtracting one survey's estimate
from the other does not create a joint metabolic-state partition.

## Complete categorical accounting

The pure [software witness](../../src/demeter/data/nhis_diagnosis_labels.py) accepts
only the two documented response fields as native strings. It neither inspects
age nor infers type from treatment. Its exhaustive
[synthetic tests](../../tests/test_nhis_diagnosis_labels.py) exercise the following
complete partition. Counts refer to input records, not an admitted population.

| Diagnosis response | Type response | Recorded category |
| --- | --- | --- |
| Yes (`1`) | Type 1 (`1`) | `reported_type1` |
| Yes (`1`) | Type 2 (`2`) | `reported_type2` |
| Yes (`1`) | Other (`3`) | `reported_other_diabetes` |
| Yes (`1`) | Blank, refused (`7`), not ascertained (`8`), unknown (`9`) | `reported_diabetes_type_unknown` |
| No (`2`) | Blank structural skip | `no_reported_diabetes` |
| Blank, refused, not ascertained, unknown | Blank | `diagnosis_unknown` |
| Any response other than Yes | Any nonblank type response | `inconsistent_type_universe` |

Unknown diagnosis is not a negative answer. Unknown type after a positive
diagnosis is not type 2, type 1, or no diabetes. A nonblank type outside the stated
universe remains an explicit inconsistency. None of these categories is overall
metabolic health. Undocumented codes or malformed inputs are refused rather than
coerced into a documented response. Native blank and unknown response codes
remain distinguishable in the input; the coarse partition is not their archive.

The witness returns a conserved private aggregate ledger and explicit
validation-only gates. It exposes no CLI, participant parsing, national estimate
or public release policy. Its in-memory functions do not themselves confer source
admission; a future empirical entry must independently check the frozen source,
code, evidence definitions and public-output contract before calling them.

## Required survey formulation before an empirical run

For a declared survey domain `D` and recorded category `C`, the proposed ratio is
`sum(w * I(D) * I(C)) / sum(w * I(D))`. Retain all eligible annual design rows,
including rows contributing zero to that domain. Category proportions must sum
to one, including unknown and inconsistent responses. Do not change the
denominator to only respondents with a known diagnosis/type without naming that
different conditional estimand.

The [2025 survey description](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2025/srvydesc-508.pdf),
PDF 47-48, specifies annual weights and a public-design with-replacement
approximation using `PSTRAT`/`PPSU`. A future estimator must preserve the full
joint category/domain covariance. Pointwise intervals are not independent
probability draws or a simultaneous region for a clinical initializer. Sampling
uncertainty does not resolve item nonresponse, reporting error or noncoverage.
Interval conventions and NCHS reliability/release checks must be explicitly
verified and frozen before choosing published results; the witness implements
none of them. Survey-description PDF 35-36 cautions that the PSU-minus-strata
degrees-of-freedom rule is not directly applicable to NHIS. Reusing a NHANES
helper's t interval does not establish an official NHIS interval convention.
Singleton-stratum handling must be declared and tested. The NCHS reporting
checklist documents SUDAAN's `MISSUNIT` convention; a chosen alternative estimator
must not silently drop a stratum or call its own refusal an official NHIS rule.
An unavailable variance under a chosen estimator is not clinical identification.

The [2025 reporting checklist](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2025/2025-NHIS-PRICSSA-508.pdf),
PDF 3, recommends Korn-Graubard modified Clopper-Pearson proportion intervals and
the [NCHS proportion presentation standards](https://www.cdc.gov/nchs/media/pdfs/2024/09/sr02_175.pdf).
Those standards assess denominator/effective sample size, interval width and
applicable degrees of freedom; they are distinct from privacy rules. The cached
standards include documented 2018/2021 corrections. The checklist also warns
that published restricted-design variances may differ from public-design
reconstruction. Preserve a failed comparison rather than tune an interval to
match it or claim NCHS endorsement.

Age/sex domains must be chosen and committed before participant-value inspection.
Unknown age or sex must remain accounted for. The 85+ public age interval must
not be split across older engine ages without a separate supported assumption.
The survey targets civilian noninstitutionalized adults, not the entire U.S.
population or children. Knowledgeable proxy interviews are permitted for adults
unable to respond (survey-description PDF 17/121). Retain proxy interviews in the
target denominator and report known/unknown proxy coverage. Use "reported"
diagnosis rather than claim that every answer is self-reported by the adult.

The 2025 design changed and collection was interrupted. Survey-description PDF
10 excludes January 2026 interviews from the annual file and explains shifted
month/quarter codes. The nominal year is not an individual clinical clock.
This is one cross-section, not repeated-person follow-up or an annual hazard.

## Admission, falsification and remaining boundary

Before participant acquisition, commit a separately reviewed intake protocol
binding exact advertised source format, documentary identities, population,
field/universe rules, missingness, age/sex domains, weights, uncertainty,
reliability, rights, output policy and calculation tests. Preserve raw bytes and
failed attempts. Freeze independent source identities and actual loaded
calculation/helper identities before the first selected-value calculation.
Unverified values remain unresolved. Expert scientific review can remain pending
while authorized bounded engineering proceeds; it is not invented intake consent.

Required checks include complete category conservation; structural skip versus
unknown type; all documented code combinations; inconsistent-universe coverage;
zero/empty domains; unknown and top-coded ages; full-design domain zeroes;
independent weighted-ratio/covariance reproduction; source/version refusal;
unchanged model trajectories; and failure to identify clinical type or transitions.
Preserve failed tests and incompatible published targets. The present witness
covers only response classification and private aggregate conservation.

All five gates remain false: `direct_initialization_allowed`,
`clinical_fit_allowed`, `engine_activation_allowed`,
`sampling_distribution_assumed` and `scientific_release_ready`.
The five existing v0.1 scientific blockers are unchanged. Even an accepted
reported-type2 benchmark would leave undiagnosed type, clinical error,
full-population/calendar transport and transition identification unresolved.

This is used-source development: producer descriptions and codebook tabulations
were inspected before this design and before any proposed empirical run.
It is not preregistration, an independent holdout or human expert endorsement.
Author context: Codex-assisted work for the Food is Health-affiliated project;
external scientific review and human conflict disclosures remain separate.
