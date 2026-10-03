# NHANES III repeat FPG observations: next-step design

Status: proposed design for the v0.1 health slice and [#57](https://github.com/Crusonia/Demeter/issues/57). This is not a frozen intake protocol, a participant-data admission, an implemented adapter or a fitted model. It adds no evidence parameters and clears no scientific gate.

Before mapping one lab measurement to a lasting metabolic state, this step checks whether its recorded label persists at a repeat visit. That informs observation-model design while health-benefit forecasts remain unresolved. Here, positive means a recorded FPG threshold label, not diagnosed diabetes.

The next useful test is small: among explicitly selected repeat respondents, does a first threshold-positive fasting-plasma-glucose observation necessarily remain positive at the designated repeat examination? A counterexample would reject deterministic persistence of that recorded label. It would not identify diabetes remission, assay-error rates or latent clinical transitions.

This feeds I-01/I-07/I-11/I-12 -> F-08 -> T-05/T-08 in the [input](04_MODEL_INPUTS.md) and [formulation/test](05_FORMULATION_AND_TESTS.md) registers. It addresses observation consistency in the health part of Q-03/RM-04; it establishes neither the dietary bridge F-04 nor the payer-cost part of P-02. The [clinical observation contract](../CLINICAL_OBSERVATION_CONTRACT.md), [program vision](../PROJECT_VISION.md), [architecture](../SYSTEM_ARCHITECTURE.md) and [active objective](../CODEX_V0_1_OBJECTIVE.md) remain authoritative.

## Source basis and review chronology

The [NCHS catalog](https://wwwn.cdc.gov/nchs/nhanes/nhanes3/datafiles.aspx) identifies NHANES III as the historical 1988-1994 survey. Its release 1A and second-exam release 3A advertise public documentation and native ASCII data with SAS layouts. This repeat resource is distinct from the current 2021-2023 assay package and does not establish transport across assay methods or vintages. The [3A README](https://wwwn.cdc.gov/nchs/data/nhanes3/3a/readme.txt), Guidelines for Data Users, identifies SEQN for linkage and explains that files have different record sets.

[Selvin et al. (2007)](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/412871), DOI 10.1001/archinte.167.14.1545, Methods: Study population and Table 3, provides the adult, fasting and FPG threshold context. Its outcomes and the producer codebooks were inspected before this design; producer frequency columns were encountered during field-definition review. This is used-source research, not preregistration or an untouched holdout. No participant files were acquired or inspected and no new empirical statistic calculated for this record.

Local documentation-only receipts and raw hashes were reviewed, and selected appendix/clock pages were visually checked. The ignored mapping JSON has SHA256 `e2eac417a3bdd45effe029e9d4b31443ac15ca54ae046a3560c4d91c81c0470a`; the independent synthetic parser/denominator draft has SHA256 `540b9de53c5e24cbeb5e5e62e3c99b7ca6cd3733e5be9c767d105de4a84d497d`. The old parser draft's observed-clock-range and gate recommendations are superseded by the additive clarification with SHA256 `72d69506788933a14bec7cfb025f2afc28a0e2ba2063e506b70b266af559d352`; its original bytes remain preserved. These identify prior local review artifacts, not a committed source package or a public replay proof. A later intake must admit reproducible source receipts and implementation identities separately. All previous protocols, reports, raw documents and receipts remain unchanged.

The [CDC use policy](https://www.cdc.gov/other/agencymaterials.html) describes most agency material as public domain with exceptions; the producer README requests NCHS acknowledgement. Local document inspection does not confer a blanket license for third-party papers or joined participant exports. Verify exact source-use terms before any participant intake or distribution.

## Known field meanings and proposed subset

The smallest implementation would select primary LAB, repeat LABSE and adult household fields privately, keeping opaque keys in memory. It would examine FPG only. A1c, OGTT, treatment effects, clinical likelihood fitting and national prevalence estimation are separate work.

| Role | Source fields and native units | Verified locator and remaining choice |
| --- | --- | --- |
| Linkage | SEQN, native five-column key in each file | Producer README and SAS INPUT layouts. Preserve lexical keys/leading zeros; reject duplicates and malformed keys. Extra primary records outside the repeat frame are not orphan errors. |
| Age | LAB MXPAXTMR, months at primary MEC exam | [LAB layout](https://wwwn.cdc.gov/nchs/data/nhanes3/1a/lab.sas), columns 1236-1239. Proposed adult rule is 20 years, expressed in months. Freeze this clock and its full missing/top-code dictionary; do not substitute interview or ADULT age. |
| Reported history | Adult HAD1 | [Adult dictionary](https://wwwn.cdc.gov/nchs/data/nhanes3/1a/ADULT-acc.pdf), PDF page 171, column 1561. Proposed subset is literal No (code 2), which explicitly includes borderline/prediabetic responses. Codes 8/9 and blank retain their source meanings. No is not absence of prediabetes or complete lifetime history. |
| Fasting | LAB PHPFAST / LABSE PHRFAST, hours | [Primary LAB dictionary](https://wwwn.cdc.gov/nchs/data/nhanes3/1a/lab-acc.pdf), pages 69/119; [LABSE dictionary](https://wwwn.cdc.gov/nchs/data/nhanes3/3a/LABSE-acc.pdf), pages 42/77. Proposed rule is at least 8 hours at each draw. It uses calculated fasting, not session instructions. |
| Reference plasma glucose | G1P / G1R, mg/dL | Primary LAB page 93 and LABSE pages 65/71. Proposed positive rule is at least 126 mg/dL. Decode the applicable-blank sentinel 88888 and whitespace missing values first; neither is a high measurement. SGP/SGR chemistry glucose is not interchangeable. |
| MEC context and recorded interval | LAB MXPSESSR; LABSE MXRSESSR and MXPRDAYS | LAB layout column 1234; [LABSE layout](https://wwwn.cdc.gov/nchs/data/nhanes3/3a/labse.sas), columns 6 and 9-10; LABSE page 39. Freeze complete session codes and the evidence establishing two MEC observations. A session code alone does not prove specimen context. |

These are proposed source-definition choices, not active cutoffs or parameters. Before calculation, register the substantive definitions and their provenance. The FPG-only, literal-HAD1-No subset deliberately differs from the publication, which also required A1c completeness. Its pregnancy-related history exclusion algorithm has not been reproduced. Do not tune selections to its published cohort size or claim reproduction of that cohort.

HAD3/HAD4 pregnancy-history routing must not become a current-pregnancy flag or default negative diagnosis. Household insulin/pill responses and at-draw screening describe different source roles. A missing screening response is not No; insulin-related OGTT omission does not automatically invalidate a measured first plasma draw. Freeze how documented omission conflicts are retained or excluded before using those fields.

## Clocks and survey design

MXPRDAYS documents days between designated examinations, with positive recorded days, `00` none/never and blank distinguished. The page-39 frequency table reports an observed span; it does not establish a scientific maximum or an admissible-value bound. Do not enforce that span as parser validity. It is usable as recorded visit context, subject to source-supported MEC scope and actual record coverage. It is not an exact sample-to-sample timestamp. PHPBEST/PHRBEST contain time of day only; do not add their difference to exam days to manufacture collection hours or fill unknown intervals with a published mean.

[EXAMSE](https://wwwn.cdc.gov/nchs/data/nhanes3/3a/EXAMSE-acc.pdf) pages 768-769 define separate MXRRDAYS/HXRRDAYS clocks. Page 772 documents home examinations that occurred before the MEC examination but were designated second and assigned a positive interval. Positive HXRRDAYS therefore does not prove forward chronology. Do not reproduce the producer-listed keys, coalesce either field into MXPRDAYS or infer biological event order. The minimal selected field set can omit both EXAMSE clocks; a later consistency study would need its own predefined disagreement rule.

LABSE Appendix 1, pages 85/87, permits home collection for adult glycated hemoglobin and does not mark reference plasma glucose/OGTT for home collection. This supports a narrower reference-FPG proposal; it does not settle every record's context. If context is unresolved, retain untimed or excluded coverage rather than claim a timed pair.

LABSE pages 10-11 describe a nonrandom repeat subsample without dedicated survey weights/design and advise against importing primary-sample design variables. Official primary files legitimately contain those columns. Exclude them from the selected analysis projection and refuse their use or national survey estimators; do not reject an official raw primary file merely for containing its documented weights. Generic weighting text elsewhere does not override this repeat-specific guidance.

## Denominators and falsification

Retain a conserved ledger from released repeat records through primary/household linkage, eligibility, assay availability and recorded-interval availability. Unmatched repeat links, unknown eligibility, missing assays and none/unknown intervals remain explicit. Primary nonrepeat records are not an invitation frame, deaths or independent censoring.

Eligibility is a conjunction: any known failed clause excludes the record; otherwise an unknown clause leaves eligibility unknown; only all passed clauses establish eligibility. Keep clause-specific coverage and a frozen first-failure order, so overlapping reasons are not summed as disjoint people. Use separate primary-only/repeat-only/both/neither assay availability and keep unknown clock coverage outside the timed diagnostic.

Privately test `first_positive -> repeat_positive` on the declared qualifying pairs. The result is:

- **Not evaluable:** no qualifying pairs or no first-positive support. Do not return a vacuous pass.
- **Contradicted:** at least one qualifying first-positive/repeat-negative pair.
- **Not contradicted in observed pairs:** positive support exists with no observed counterexample.

These labels refer only to the recorded rule in a selected sample. They do not establish clinical confirmation or identify measurement error separately from physiological change, collection conditions or selection. A short interval does not establish biological constancy. No national uncertainty, T2D subtype, mortality process, long-term remission, causal dietary effect or clinical annual hazard is identified by two assays.

## Prerequisites for an implementation PR

1. Complete the selected age/session/screening code dictionaries and context argument. Freeze native layouts, units, missing codes and decimal parsing; SAS display FORMAT is not implied input scaling. Published observed ranges are not biological validity bounds. LAB and ADULT positions differ and cannot share a decoder.
2. Freeze the exact subset, ledger order, conflict policy, recorded-time interpretation and privacy schema. Public output may contain reviewed coverage and an evaluation status, but no keys, assays, labelled paired cells, witness records or margins that reconstruct those cells. A singleton or otherwise isolating eligible group requires withholding under a rule fixed before outcomes; deleting individual rows to clear a privacy test is unacceptable.
3. Commit an additive used-source protocol before participant acquisition. Then acquire original public bytes with immutable receipts and independently admit source bytes plus actually loaded code hashes before the first diagnostic run. Preserve prior evidence records and frozen reports. A mutable registry/manifest cannot alone reseal the source or implementation.
4. Build the smallest pure source adapter and logical diagnostic, with meaningful synthetic tests: paired swaps with unchanged margins, empty/zero-positive support, missing-as-zero, conflicting/unknown context, source-specific layout drift, duplicate/unmatched linkage, denominator conservation, weight misuse, clock substitution, private-output refusal and coherent source/code self-repinning. Frozen aggregate replay follows empirical execution; synthetic checks establish software behavior only.

Any conditional resampling interval would require a separately justified exchangeability model. The first diagnostic can report finite selected-source support without claiming a population interval. Its eventual role remains benchmark-only/validation-only. The canonical gates `direct_initialization_allowed`, `clinical_fit_allowed`, `engine_activation_allowed`, `sampling_distribution_assumed` and `scientific_release_ready` must all remain false. Public-exposure fitting, T2D mapping and other unsupported interpretations are separate restrictions, not substitute gate keys. This design record does not implement a new parser, change annual health mechanics or activate any of those capabilities.
