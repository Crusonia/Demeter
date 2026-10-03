# HRS repeat-biomarker source checkpoint

HRS documents HbA1c measurements collected in 2012 and 2016 that could help
Demeter check whether a recorded glucose-related label persists on another
visit. Before treating one measurement as a lasting metabolic state, we need
to understand repeat measurements and who could be measured again. This is
source discovery as of October 3, 2026, with no participant intake, estimates,
clinical rates or new model inputs.

This checkpoint feeds I-11 observation design, with I-01/I-07/I-12 and
F-08/T-05/T-08 in the [design inventory](design/README.md) and
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md). It preserves
the [active objective](CODEX_V0_1_OBJECTIVE.md). The
[authored metadata receipt](validation/hrs-repeat-biomarker-source-checkpoint-v1.json)
records URLs, locators, access failures and used-source evaluation chronology.

## Which repeat resource is documented?

The producer lists [2012 dried-blood-spot (DBS) data](https://hrsdata.isr.umich.edu/data-products/2012-biomarker-data)
(April 2015 Final V1.0, DOI 10.7826/UVTJ1509) and
[2016 DBS data](https://hrsdata.isr.umich.edu/data-products/2016-biomarker-data)
(November 2020 Early V1.0, DOI 10.7826/GDSJ6138).
Collection year and release year describe different events.

The [2016 producer description](https://hrsdata.isr.umich.edu/sites/default/files/documentation/data-descriptions/1789588906/HRS%20Data%20Documentation%20for%202016%20DBS%20Release.pdf)
(page 2) describes rotating repeat groups: one returns in 2006/2010/2014 and
the other in 2008/2012/2016. Adjacent survey waves are not automatically paired
biomarker visits. Actual 2012/2016 paired membership has not been inspected.

The [2012 native codebook](https://hrs.isr.umich.edu/sites/default/files/meta/bio2012/codebook/biomk12bl_r.htm)
names `NA1CUW`; the [2016 native codebook](https://hrs.isr.umich.edu/sites/default/files/meta/bio2016/codebook/biomk16bl_r.htm)
names `PA1CUW`. These are University of Washington HbA1c observations, in percent
according to the producer description (pages 3–4). Character `HHID` and `PN`
fields describe cross-wave linkage.

`NA1C_ADJ` and `PA1C_ADJ` are separate NHANES-equivalent observations. The producer
warns that longitudinal differences in adjusted HbA1c “will reflect differences,
or change over time, in NHANES values” (2016 description, page 8). Keep native
and adjusted observations separate. Two assays alone cannot identify how much
change is biological versus measurement variability.

## Verified roles and remaining limits

| Question | Documented role | Limit for model design |
| --- | --- | --- |
| Who was eligible? | [2016 Section I](https://hrs.isr.umich.edu/sites/default/files/meta/2016/core/codebook/h16i_r.htm) `PPMELIG` distinguishes biomarker eligibility from nursing-home, proxy, telephone and next enhanced-interview-group categories. | Eligibility in this wave does not establish a representative paired panel of all HRS respondents or all U.S. adults. HRS concerns an older population; age and transport rules require a separate contract. |
| Was blood collected successfully? | `PI922` records consent. `PI923` asks about attempting completion despite its complete label. | Neither proves a valid specimen or HbA1c. `PI924M*`, `PI943M*` and `PI926M*` hold multiple reasons/problems, not an exclusive attrition partition. |
| What history was reported? | [2012 Section C](https://hrs.isr.umich.edu/sites/default/files/meta/2012/core/codebook/h12c_r.htm) `NC010` and [2016 Section C](https://hrs.isr.umich.edu/sites/default/files/meta/2016/core/codebook/h16c_r.htm) `PC010` concern diabetes or high blood sugar; prior reports may be carried forward or disputed. | Disputed history is not confirmed remission. Conditional diagnosis-year blanks do not mean no history. |
| Is diabetes type known? | `PC285` distinguishes reported sugar-condition stages, including diabetes and borderline/prediabetes. | Stage is not Type 1/Type 2. No explicit type question was verified in these inspected diabetes blocks; insulin and oral medication do not identify type. |
| Can the panel represent the population? | `NBIOWGTR` is a 2012 biomarker respondent weight; tracker `PBIOWGTR` is the 2016 biomarker subsample weight. | A wave weight is not a verified paired-panel weight or selection correction. |
| Are deaths and nonattendance identified? | The [tracker codebook](https://hrs.isr.umich.edu/sites/default/files/meta/tracker/codebook/trk2022tr_r.htm) distinguishes reported alive, presumed alive, known deceased and not in sample; death and last-alive dates retain source information. | `PALIVE` alive status can rely on reports; presumed alive can mean no contact. Neither guarantees complete ascertainment. Reported and imputed death dates must remain distinct. |
| Is elapsed specimen time known? | Tracker interview year/month fields mark interview starts; collection instructions mention dates on forms. | Neither proves released DBS draw dates. No draw-time field was verified in the inspected DBS BL and 2016 I inventories; this is not a claim about all HRS products. |

The [tracker catalog](https://hrsdata.isr.umich.edu/data-products/cross-wave-tracker-file)
lists December 2025 Final 2022 V1.0 (DOI 10.7826/OZGE2932). A future adapter must
pin exact versions and retain unknown, inapplicable, report-source and sample
disposition meanings. Missing assays cannot automatically become losses or deaths.

## Why venous blood is separate

The [2016 venous-blood study (VBS)](https://hrsdata.isr.umich.edu/data-products/2016-venous-blood-study-vbs)
lists April 2025 Final V3.0 (DOI 10.7826/ORTM1684). Its
[native codebook](https://hrs.isr.umich.edu/sites/default/files/meta/vbs/2016/codebook/vbs16v3a_r.htm)
includes fasting glucose `PGLUFF`, fasting report `PFASTYN`, an interview-to-draw
day offset `PVBS_N_DAYS` and collection time `PVBSCOLTM`. No verified bridge
applies that VBS offset to DBS observations.

The [2016 supplemental release](https://hrsdata.isr.umich.edu/data-products/vbs-2016-supplemental-file)
and [neuropathological/supplemental release](https://hrsdata.isr.umich.edu/data-products/vbs-2016-neuropathological-and-supplemental-biomarkers)
add assays to a 2016 specimen; they are not new collection visits. Availability
of later biosamples also does not establish a released counterpart assay. No
actual repeat VBS assay product was verified in this bounded check; other HRS
resources may warrant review.

## The smallest useful next design

A synthetic observation/disposition witness could preserve native versus adjusted
assays, carried-forward/disputed reports, consent/attempt/validity, reported versus
presumed alive and unknown clocks. It could refuse unsupported clock, type and
population-weight claims before a source-specific implementation is proposed.

A future benchmark could test recorded HbA1c-label persistence among explicitly
linked, selected respondents. Without specimen dates, this would be a nominal
collection-wave comparison, not a timed transition model. Before empirical intake,
document exact source bytes, processing/reuse terms, formats, sentinels, linkage,
diagnosis universes and selection/disposition. Fix the estimand and a
nonreconstructive disclosure rule in a committed used-source protocol, then admit
reviewed code before diagnostics. A population estimate additionally needs a
justified paired design and weight prescription. Empty data or zero first-label
support must be not evaluable. This proposal implements no parser or benchmark.

Even a valid repeat-label benchmark would not identify latent metabolic states,
Type 2 diabetes, remission, clinical hazards, independent censoring or dietary
causal effects. All five gates remain false: `direct_initialization_allowed`,
`clinical_fit_allowed`, `engine_activation_allowed`, `sampling_distribution_assumed`
and `scientific_release_ready`.

## Access and evaluation chronology

This was a chosen anonymous metadata-only scouting procedure within the broader
public-source search. Ordinary web display supplied documentary findings. Nine
unsigned documentary requests returned HTTP 403 and supplied no original source
bytes; their receipt contains null original hashes. Later successful codebook
display does not rewrite those failures. Research-artifact hashes identify our
authored notes, not producer files or admitted scientific evidence.

HRS sensitive-health access conditions are separate from metadata visibility.
No account, agreement, participant acquisition or access workaround was used.
Registration is not automatically a judgement about scientific suitability;
participant processing and redistribution rights were not established here.
No publisher full text, frequency tables or participant records are included.

Sources and publication summaries had already been examined. This is used-source
evaluation, not preregistration or independent validation. Earlier notes remain
unchanged; this checkpoint adds the clarification that alive status can be
report-based. The [scientific review policy](SCIENTIFIC_REVIEW.md) separates
software checks, scoped scientific assessment and release readiness.
