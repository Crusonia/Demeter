# HAALSI repeated-glucose documentation: useful fields, unresolved clocks

Status: metadata appraisal only. The [ICPSR V4 catalog](https://www.icpsr.umich.edu/web/NACDA/studies/36633), DOI 10.3886/ICPSR36633.v4, describes HAALSI in Agincourt, South Africa. Root obtained the codebook, questionnaire and crosswalk through ordinary provided documentation-only browser links. An earlier ordinary HTTP codebook request was refused. No account, assent, participant file or access workaround was used. Original documents remain ignored and unredistributed. This is used-source review: printed descriptive summaries were incidentally visible, but no outcome count, mean or ratio is selected as a target or finding.

The [terms page](https://www.icpsr.umich.edu/web/ICPSR/studies/36633/terms) was inspected by root in an ordinary browser. This appraisal has no HTTP terms receipt. The terms restrict subject identification and redistribution of data or other materials, subject to stated exceptions and agreements. Public document visibility is not an open-data license. This documentary review creates no new approval requirement or participant request.

## Concrete observation fields

| Role | Exact fields and 1-based PDF pages | Boundary |
| --- | --- | --- |
| Linkage | `PRIM_KEY`, codebook 5, printed 2; character width 5. | No participant file acquired or identifiers extracted/matched; no linkage performed. Native row unit, cross-wave linkage, uniqueness and aliases remain source-admission questions. |
| Repeated glucose | `W1C_BS_GLUCOSE`, 1146–1147; `W2C_BS_GLUCOSE`, 2547–2549; `W3C_BS_GLUCOSE`, 3817–3819. Each is labelled point-of-care glucose in mmol/L. | Not inherently fasting, an OGTT, plasma-confirmed diabetes or T2D. First-50 continuous summaries are not validity limits. |
| Disposition | `W2STATUS`, 1326, printed 1323; `W3STATUS`, 2599, printed 2596. Codes 0 died, 1 completed, 2 refused, 3 not found, 4 incomplete. | Distinguishes deaths and nonattendance, but supplies no individual death date, last-contact clock or verified cumulative/interval event ordering. |
| Interview mode | `W2INTERVIEW_TYPE`, 1326; `W3INTERVIEW_TYPE`, 2599. | Mode/completion is separate from assay availability and clinical state. |
| Fasting | `W1C_BS_HRSLASTATE` and `W1C_BS_FASTING8HR`, 1172, refer to DBS collection start. `W2BS051`, 2214–2216, is a character field of width 15. | Alignment to the glucose specimen and native elapsed-time grammar are unverified. A wave 3 fasting counterpart was not identified in the bounded index search. |
| Interview anchors | W1 month/year, 1176–1177; W2 year, 2566–2567; W3 month/year, 3836. | `W2C_INT_MONTH`, 2567, is labelled interview day despite its name. Do not silently choose month/day or substitute interview anchors for specimen/death dates. |
| HbA1c boundary | Hemoglobin fields at 1147, 2549 and 3819 are in g/dL. Questionnaire 115 has `CE201_form4` HbA1c consent. | No HbA1c assay-value field was identified among the codebook's 6,157 bookmarked headers. Consent is not concentration or proof of release; this does not establish absence throughout HAALSI. |

Both status variables display missing placeholders -99 empty, -98 don't know and -97 refused. Placeholder -97 is distinct from status 2 refused. The printed labels do not establish native Stata/delimited missing encodings. Separately, our future handling policy retains any unlabelled/system missing as unknown, never as death or a healthy state; that policy is not an observed codebook label. Glucose flags are also separate: W1/W2 display 1 yes and 2 no, but flag direction requires verified cleaning definitions. W3's numeric flag lacks a verified complete labelled dictionary here. Earlier-wave codes cannot be transplanted.

No respondent-specific death-date, last-contact, censoring-time or survey-weight field was identified in the bounded header searches. Relatives' death questions are excluded from respondent mortality evidence. Body weight is not a sampling weight, and weights would not replace an event history. These are scoped search results, not claims that no such HAALSI product exists.

## Source contradictions remain visible

The crosswalk says it does not yet reflect wave 3. Questionnaire PDF 3 has a Wave 2 / 2021–2022 heading, a W3 note, and warns that instrument variables may be omitted from released data. Its later created-variable table references `w3endtime`. It cannot safely establish baseline-only or every-wave semantics.

Questionnaire 60 gives `BS051` hours-since and minutes-since prompts, but does not establish the released W2 character field's serialization. Card and results-date instructions on 60 and 62 are not released per-record timestamps. Pages 115–116 derive interview month/year from `w3endtime`; `c_int_time` is labelled begin time while referring to that end-time source. No matching released specimen clock is verified.

Questionnaire 98 labels SRDIAG broad/ever-diagnosed and SRTRT narrow/current-treatment, while its diagnosis/treatment descriptions attached to `cm007_males/females` and `cm010` are reversed relative to those questions. Crosswalk rows 2847–2848 reverse broad/narrow associations relative to the questionnaire. The questionnaire uses inclusive glucose operators; the crosswalk uses greater-than wording. Its strictly greater than 8 hours fasting rule and missing-fasting-as-nonfasting convention differ from the codebook's at-least-8-hours flag. W3's SRDIAG label also mixes diagnosis and treatment. No operator, name, pointer or missingness convention is silently corrected, and no cutoff is admitted as a model parameter.

## Useful next scope

This is a concrete lead for a conditional private comparator of repeated recorded glucose/diagnosis and wave dispositions. Before values, resolve permitted source use, native linkage and missingness, wave-specific fasting, derived-definition disagreements, dated observation/death/last-contact anchors, repeat-selection and population transport. Freeze a finite source/observation/privacy contract. Preserve refused, not-found, incomplete and unknown paths; do not treat them as healthy, dead or independently censored. Nominal wave intervals do not identify annual hazards or a U.S. T2D initializer.

The [companion metadata appraisal](validation/haalsi-icpsr-v4-documentation-appraisal-v1.json) pins the three actual original documents and acquisition receipts, exact PDF/printed-page locators and selected page-text hashes. Original instruments are not redistributed. All five scientific gates and source admission remain false. No participant acquisition, empirical calculation, fitted rate, registry change or engine activation occurred.

This additive version corrects the earlier candidate's missing-label attribution and linkage wording. Original documentary bytes, selected page hashes and the earlier candidate remain preserved. Printed pseudonymous values may have been incidentally visible; none were extracted or matched.
