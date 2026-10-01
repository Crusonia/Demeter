# Stanford iPOP/iHMP source coverage

Stanford iPOP/iHMP is a concrete candidate for linked, repeated laboratory
observations in a native volunteer cohort. Public producer code and selected
headers establish a possible subject–sample–measurement linkage. They do not
yet establish a fit-ready clinical panel, a national population model or a
dietary effect. No clinical values, transitions or mortality rates were fitted
in this appraisal.

This work supports [#57](https://github.com/Crusonia/Demeter/issues/57) within
the [v0.1 health slice](PROJECT_VISION.md). The health design chain is
Q-03/RM-04 -> P-02 -> I-01/I-07/I-11/I-12 -> F-04/F-08 ->
T-01/T-05/T-06/T-08; L-00 supplies bookkeeping only. The
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) and
[longitudinal likelihood](LONGITUDINAL_LIKELIHOOD.md) retain separate source,
identification, estimation and activation gates.

## Source identity and permission

The primary studies are [Longitudinal multi-omics of host–microbe dynamics in
prediabetes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6666404/)
(DOI `10.1038/s41586-019-1236-x`) and
[A Longitudinal Big Data Approach for Precision Health](https://pmc.ncbi.nlm.nih.gov/articles/PMC6713274/)
(DOI `10.1038/s41591-019-0414-6`). Their methods describe fasting clinical
assessments, scheduled visits and additional illness/event visits in a recruited
volunteer population. The companion paper describes public clinical laboratory
data through 2016 and a separate controlled-consent route. Later study
measurements must not automatically be assigned to that public release.

The first study's public-data statement describes CC0 data and MIT software.
The derivative [TemporalMultiomicsDiabetes repository](https://github.com/gmiaslab/TemporalMultiomicsDiabetes/tree/ba55996cb51a8bc4fbe9374633e9cb3223c6ea8c)
has a MIT code license. More directly, [Zheng et al. (2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9284494/),
Methods “Summary of cohort details and data” and Data availability, identifies
the original authors' publicly available Stanford data and explicitly names this
repository and Zenodo DOI `10.5281/zenodo.6751960` as its released analysis files.
Together with the pinned README's source mapping, this establishes credible
author-declared public provenance for the named derivative release. Independently
certifying every person's consent is not an additional gate to its research use.

The [provenance correction](validation/ipop-public-provenance-correction-v1.json)
supersedes the earlier unresolved-public-membership interpretation while preserving
the original frozen protocol and acquisition receipts. It does not certify an
unverified copy, expand the public HMP release through 2018 or establish raw assay
values. Exact calendar coverage remains a descriptive question; it need not block
an analysis confined to the author-declared public derivative. The inspected
commit is `ba55996cb51a8bc4fbe9374633e9cb3223c6ea8c`, with root tree
`021c4dfe091d3e554b3173711ab01fc06da15141`. Its bytes are not silently equated
with the separately identified Zenodo release/tag.

The [schema protocol](validation/ipop-schema-protocol-v1.json) was committed
before the selected header requests. It is used-source documentation work:
publication methods and producer code were already inspected, and publication
results were incidentally exposed. This is not a blinded evaluation or an
independent clinical validation.

## What the selected headers establish

Text locators below are the first physical line only. Workbook locators are
`VisitList.xlsx`, `Sheet1!A1:O1`; later worksheet rows were not inspected.
Header names establish labels, not the meaning or coverage of their values.

| File | Verified selected labels and possible role | Unresolved binding |
| --- | --- | --- |
| `clinical_tests.txt` | `VisitID`; laboratory columns including `A1C`, `GLU`, `INSF`, `INSU`; `SubjectID`, `CollectionDate`, `CL1`–`CL4` | Derivative assay units/rawness, fasting validity, missing codes and `CL1`–`CL4` roles; the publication names for `A1C`/`GLU` are verified below |
| `SampleInfo.csv` | `SubjectID, SampleID, Days_Since_Start, CL4`: sample/subject and relative-clock labels | Clock origin/resolution, actual collection mapping and context semantics |
| `VisitSchedules.csv` | `VisitID, SubjectID, CollectionDate, Event, Event_Note1, Event_Note2, Event_Note3, SubStudy`: visit/context labels | Actual versus planned visit, event codes, clock alignment and ascertainment |
| `VisitList.xlsx` | A1–G1: `SubjectID, SampleID, Days_Since_Start, CL1, CL2, CL3, CL4`; H1–O1: `Cytokines, ClinicLabs, Metabolites, Proteins, Transcripts, Gut_16S, Nasal_16S, Num_Type` | Whether these are availability indicators, measurements or other codes; no coverage counts inferred |
| `subjectStatus.csv` | `SubjectID, SampleID, CollectionDate, CL4`: sample-linked visit context | Clock definition and completeness; not a glycemic-state field |
| `SubjectInfo.csv` | `SubjectID, Study, Race, Sex, Age, BMI, SSPG, IR_IS_classification`: subject-level descriptors | Baseline date, derivation, missingness and relationship to glycemic observations |
| `SubjectClass.csv` | `SubjectID, Class`: subject classification | Definition, time scope, diagnostic/type/history semantics and possible future-information leakage |
| `addInfo.csv` | `SubjectID, OGTT_Number, SSPG (mg/mL), Matsuda, DI, isrMax (pmol/kg/min), cluster`: additional test/derived-label surface | Test dates, repeated-test linkage, units and derivations. Literal `SSPG (mg/mL)` is neither verified nor corrected |

The publisher's Table S0 was inspected after the exact worksheet selection was
committed. In `S0. Labs & Immune Proteins`, A4/B4 label the symbol/name columns;
A5/B5 bind `A1C` to hemoglobin A1c and A24/B24 bind `GLU` to glucose. The selected
schema has no assay-unit or platform columns. This verifies measure-name identity
alongside the matching derivative headers; it does not establish derivative
units, rawness or specimen validity. Public-source provenance rests on the
author declarations above, rather than this assay-name table.

The companion paper's Figure 2 caption reports HbA1c in percent and fasting/OGTT
glucose in mg/dL. Those publication units are relevant context, not a verified
unit declaration for the derivative files. Extended Data Figure 3 describes
same-day HbA1c tests at different laboratories; a later intake must preserve such
records rather than silently deduplicate dates. No clinical threshold or category
conversion is introduced here.

## What producer code establishes

Locators refer to the original notebook JSON: `cells[]` indices are zero-based;
source-line numbers are one-based. Only code-cell sources were inspected, without
execution. Original notebook bytes were transported and hashed in memory; stored
outputs were not inspected, rendered or retained.

“Single” is `code/Single subject analysis.ipynb`, Git blob
`2588dd2feb2fc86fa3d22837c3bbb53b05769c5a`; “multi” is
`code/Multi-subject similarity analysis.ipynb`, Git blob
`4fd94fb8fb161e9bb3c4004fc152d719c46dae83`, at the pinned commit above.

| Operation | Exact code locator | Interpretation |
| --- | --- | --- |
| Clinical linkage | Single-subject cell 3, lines 2–5; multi-subject cell 4, lines 2–5 | Read TSV, drop `SubjectID`, original `CollectionDate` and `CL1`–`CL4`, suffix laboratory columns, then rename `VisitID` to `SampleID`. No analyte/value/unit/reference-range role for `CL1`–`CL4` is established |
| Analysis clock | Single cell 4; multi cell 5, lines 3–8 | Join `SampleInfo` and `SubjectClass` on `SubjectID`; append `Class` to identifiers; rename `Days_Since_Start` to `CollectionDate` and cast to integer. Original clinical dates are not parsed |
| Sample join | Single cell 6, lines 7–10; multi cell 7 | Outer join on `SampleID`, delete selected missing observations and cast the derived clock to integer. This does not verify unique keys or join cardinality |
| Visit context | Multi cell 22; cell 23, lines 9–16; cell 34, lines 11–17 | Read `subjectStatus`, cast/sort its `CollectionDate`, use `CL4` prefixes for Healthy/Infection/Immunization/Weight change/Antibiotics/Others. “Healthy” here is visit context, not normal glycemia |
| Additional tests | Multi cell 25, lines 2–5 | Drop `OGTT_Number` and average by `SubjectID`, losing repeated-test chronology in that derived output |

The analysis also applies coverage/missingness filters, generic numeric coercion
and signal normalization. Those processed outputs are not raw clinical
observations. The inspected notebooks do not use `VisitSchedules.csv` or
`VisitList.xlsx`; their headers therefore add schema evidence beyond the code.
Absence of a death or treatment mapping in these two notebooks does not prove
absence from the original study.

The companion study describes later classifications using follow-up measurements.
Until its definition is bound, `SubjectClass.Class` cannot initialize a baseline
state or locate onset. A later low laboratory observation must not erase a known
diagnosis or establish remission. Insulin-resistance classification must not be
silently equated with prediabetes or comprehensive metabolic health.

## Acquisition is separate from inspection

The seven text files were requested from commit-pinned public URLs. Successful
header reads retain partial bytes and their hashes; they do **not** verify the
complete source file or its pinned Git blob. The workbook required full binary
acquisition and remains ignored, fetch-only storage containing uninspected record
content. Its 74,029 bytes match Git blob
`357b1c774c66ebdc3c1a624206210a5d31782088` and SHA256
`ab885e2b990894c4d9bbec6d99fa6a4160bf5e905265ee18e7e38f22e4b6aef0`.
Only structural metadata and row 1 were inspected; shared-string values were
resolved solely for those header cells. No workbook record rows were inspected.

Default-network failures were preserved. The first successful-network clinical
request used an LF-only stopping guard and failed to recognize a CR-terminated
header. It may have acquired an uninspected prefix containing record bytes,
bounded by the helper's 65,536-byte cap. That prefix was not retained, decoded,
displayed or analyzed; its exact length/hash remain unknown. This attempt must
not be called header-only. Original receipts remain unchanged.

A separate corrected request stopped at the earliest CR/LF before parsing.
The retained clinical header is 286 bytes ending in CR; verification confirms
that its only CR/LF is the final byte. Its partial SHA256 is
`966181a5b14d2aa89d6dea19697b8399f03746135d8efe52e7cece7b4d8b83ad`.
The committed [schema receipts](validation/ipop-schema-receipts-v1.json) preserve
the original attempts, correction, exact labels and this scope exception.
No clinical analysis was performed and no participant identifiers or record
values belong in the public coverage report.

The advertised PMC supplement request returned HTTP 200 HTML, not a workbook.
Its original bytes and failed assessment were retained, with a separate response
validation correcting the initial acquisition flag. The independently advertised
publisher copy was pinned in a [locator amendment](validation/ipop-schema-locator-amendment-v1.json)
before requesting it. It is a valid 680,266-byte workbook, SHA256
`0fee15e1eb0d9be7f2be363be99781e566f8c03ef1cc10b1591c8743efc34278`.
Its dotted S0 sheet name did not match the original selector; no sheet content
was read at that point. A separate [worksheet amendment](validation/ipop-schema-worksheet-amendment-v1.json)
selected that exact metadata identity before offline inspection. Only S0 schema
was then inspected; the acquired mixed workbook also contains uninspected
S1–S28 sheets. No complete supplement, notebook or participant file is
redistributed with this appraisal.

`uv run demeter data verify-packages --check-tracked` verifies the committed
artifact hashes offline. It does not retrieve the ignored source files, verify
the unread remainder of partial text acquisitions, or confer clinical eligibility.

## Candidate target and next gate

A defensible next target could be a native-cohort panel of laboratory proxies,
conditional on a source-supported observation and selection process. Actual
elapsed clocks, measurement definitions and repeated-record linkage could support
progression/reversal information beyond marginal endpoints. Exact biological
onset dates, a national population and a diabetes-remission extension are not
universal prerequisites for that restricted target.

The author-declared public derivative is an eligible candidate for a narrowly
defined intake; source-specific numerical selection still must be frozen before
record inspection. Study HbA1c percent/FPG mg/dL context, matching assay names and
producer loading before normalization support explicit measurement assumptions,
not certification that upstream derivative values are raw assays. Likewise,
`Days_Since_Start` and the producer's sample join supply a declared relative-day
clock. An unknown additive origin cancels in within-person elapsed differences;
it is not by itself a reason to reject that target. Actual collection association,
resolution, upstream transformations and key cardinality remain to be assessed.

Predeclare these assumptions and check the selected linked panel's missing/invalid
codes, repeated samples and duplicate days before any fit. Preserve originals;
do not silently infer units from value ranges, average repeated tests, invent
dates or use scheduled visits as observed dates. Compare A1c-only and GLU-only under a separately declared fasting interpretation
measurement alternatives, and scheduled versus illness/event visit context where
supported. If a required assumption cannot support the chosen estimand, report
the failed gate rather than change it to obtain a desired result.

Keep diagnosis/type history and treatment documented or explicitly unknown,
excluding dependent claims. A later estimation protocol must specify the estimand,
observation mapping, visit/selection alternatives, joint likelihood and uncertainty,
identification diagnostics and evaluation plan. Event visits must not be assumed
ignorable. These permissions do not extend to a diagnosed-state, mortality or
national model merely because a conditional laboratory-panel intake is feasible.

Death, withdrawal, last contact and administrative stopping remain unknown here.
Those gaps block dependent competing-mortality or censoring calculations, without
automatically disqualifying every conditional glycemic analysis. A source-supported
diagnosed-history state would need its own retained-history/type contract; a low
test value alone supplies neither that state nor recovery from it.

This appraisal supplies no national initialization or transport, annual biological
rates, isolated dietary causal effect, mortality estimate or engine activation.
The continuous-time observation evaluator is distinct from the annual simulation
operator. Public availability and software checks do not confer clinical
identification or scientific release readiness; #57/#58 remain open.

## Frozen linked-file preflight

The [numerical intake selection](validation/ipop-numerical-preflight-protocol-v1.json)
is frozen before complete source acquisition and selected record aggregation.
It selects only clinical VisitID/SubjectID/A1C/GLU/CL4 and
SampleInfo SubjectID/SampleID/Days_Since_Start/CL4 at the pinned commit.
The preflight tests exact association cardinality and assay-specific repeated
coordinate coverage, retaining every source row, ambiguous key, undocumented
number token and no-finite-assay subject-label complement in explicit denominators.
It introduces no clinical threshold, likelihood, fitted transition, or active
parameter. Assay units, rawness, fasting/specimen identity and relative-day
interpretation remain declared assumptions. Numerical results will be recorded
separately after verified acquisition; this freeze follows prior source appraisal
and is not independent clinical validation.
