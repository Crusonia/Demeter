# Admission decisions for new public longitudinal sources

Assessment: October 1, 2026 UTC. This continues the
[public observation requirements](PUBLIC_LONGITUDINAL_DATA_REQUIREMENTS.md) for
[#57](https://github.com/Crusonia/Demeter/issues/57). It is a documentation and
access appraisal, not a clinical fit. No participant dataset, selected outcome
count, coefficient, equation or evidence parameter is added.

For a newcomer, repeated measurements are useful because they can show which
observations belong to the same person over time. But a publication saying
"repeated tests" does not prove its public spreadsheet includes those visits.
A later low glucose result also does not erase a diabetes diagnosis or establish
untreated recovery. We must check the actual clocks, history, missingness and
selection before interpreting change. This is how Demeter grows toward an
educational management flight simulator without presenting assumptions as findings.

## Decisions

| Candidate and exact release | Verified documentation | Admission decision and next evidence |
| --- | --- | --- |
| [Korean occupational examinations, Dryad](https://doi.org/10.5061/dryad.tht76hdz4), API version 7 / version object 104844 | Dataset metadata declares CC0-1.0. The file inventory separates `dataset_final.xlsx` from `Usage_notes.xlsx`. The primary Ji et al. [BMJ Open paper](https://doi.org/10.1136/bmjopen-2020-039541) describes repeated fasting glucose/HbA1c examinations in selected male workers. | **Conditional first candidate for a finite schema gate.** Neither workbook was acquired. Resolve the separately published usage notes before proposing any record intake. The publication fields are consistent, as clarified below. Actual linked visits, clocks, retained diagnosis/treatment, death and stopping information are unverified. |
| [SLIMM-T2D](https://www.nature.com/articles/s41467-021-27289-2), [Zenodo v1.0.4](https://doi.org/10.5281/zenodo.5662430), Git tree `72519ba775c0ed6a8dff64b360bb10591b6c0167` | The paper describes fasting glucose/HbA1c and per-person, per-timepoint clinical characteristics and medication-class observations after established T2D. The versioned tree lists `data/clin_metadata.csv` and `data/medications.xlsx`. | **Conditional post-diagnosis observation lead.** Zenodo says `other-open`; the repository MIT license refers to software/documentation and the article is CC BY 4.0. Clinical-record license scope is not separately established here. Resolve that scope and a clinical dictionary before records. This entry population cannot alone supply undiagnosed progression/reversal. |
| [CRELES](https://doi.org/10.7910/DVN/7AUOAO), Dataverse v10.0, released October 27, 2025 | Live metadata remains CC BY-NC 4.0. The enabled guestbook requires name, email, institution and position. All eight listed files are ZIPs with `tabularData=false`; no separate dictionary/code file is exposed in this release. | **Keep off the unrestricted automatic intake path.** A permitted noncommercial purpose and any guestbook interaction require separate decisions. Public metadata and `restricted=false` do not establish commercial permission or anonymous replay. No guestbook response or archive acquisition occurred. |
| [Comorbidities and Outcomes](https://doi.org/10.5281/zenodo.7543862), Zenodo record 7543862 | API metadata identifies `cc-zero` and open access, while the description expressly limits access to research purposes. The inventory lists baseline/outcomes and medication/cohort CSV/XLSX files, without a separately designated clinical dictionary. | **Rights/observable scope unresolved.** Preserve both the license field and research-purpose statement; do not silently select one. File names do not establish repeated assay clocks or sufficient joint paths. No participant file or preview was acquired. |

These decisions apply to the inspected releases. They do not establish that no
other adequate public source exists, or that a fuller cohort lacks the needed
observations. No registration, credential use, access application, personal
information submission, agreement interaction or researcher outreach occurred.

## Finite next gate: the Dryad usage document

The [file-list metadata](https://datadryad.org/api/v2/versions/104844/files)
binds the separate usage document to file 579891, `Usage_notes.xlsx`,
14,313 bytes, SHA-256
`8f586fb25dc96b1430fe3f39878ccbde12e04b4a8f208a22e230616ff7962317`.
The participant workbook is a different file, 579892. This metadata establishes
file identity; it does not establish the notes' contents or record coverage.

The cached dataset and version metadata both report `versionNumber=7`,
`versionStatus=submitted`, `curationStatus=Published`, `visibility=public` and
`publicationDate=2021-02-12`. Dryad's [official documentation at a pinned commit](https://github.com/datadryad/dryad-app/blob/1039c857e10355ceafb21385864e13cc54b7c6db/documentation/apis/embedded_submission.md#L142-L154)
defines `versionStatus` as the editing/processing lifecycle and `curationStatus`
as a separate publication lifecycle. Completed resource submission is compatible
with publication; these fields do not establish a publication discrepancy.
The [submission-flow definitions](https://github.com/datadryad/dryad-app/blob/1039c857e10355ceafb21385864e13cc54b7c6db/documentation/submission_flow.md#L31-L56)
independently distinguish both fields. Curation `submitted` is another field's
state and must not be substituted for `versionStatus=submitted`.

The earlier appraisal misinterpreted `versionStatus`. Its original receipt is
preserved; the [correction receipt](validation/public-longitudinal-status-correction-v1.json)
supersedes that interpretation using pinned documentation and the unchanged
release metadata. Remove the publication-status condition from admission.
The correction does not resolve downloads or actual clinical record coverage.

The first documentation-download command was rejected by automatic approval
review because its file-stream identity was ambiguous and could imply health
record acquisition. It did not execute. After official metadata established the
separate document's identity, review accepted a bounded request for that document.
The ordinary website file-stream GET returned HTTP 403; the download link
advertised by the metadata returned HTTP 401. No usage-document bytes were
obtained. These failures do not prove that Dryad requires an account for every
public download, or that the data license changed. Do not substitute credentials,
challenge interaction or participant-file acquisition for this unresolved gate.

A contributor can supply the separately published usage document or an ordinary
accessible publisher link. Verify it against the recorded digest, retain a
changed version separately, and inspect its schema descriptions only. Before
opening records, use the notes to answer these questions:

1. Does the release contain linked observations at individual visits, endpoint
   summaries, or both? What is the actual row unit and linkage key?
2. Which fields encode assay units, fasting conditions, collection dates or
   supported intervals? Does follow-up stop at detection or at last assessment?
3. Are prior diagnosis and medication history retained? Which treatment, death,
   contact, withdrawal and missing-code fields are actually present or absent?
4. How does the released subset relate to eligibility, ferritin testing,
   exclusions and repeat-examination attendance in the paper?

The paper's general inclusion rule excludes baseline diabetes; its operational
new-diabetes definition additionally restricts baseline fasting glucose to the
normal range. Do not equate these rules or assume that the entire workbook
excludes baseline impaired fasting glucose. A schema appraisal must resolve
which rule applies to which released rows and endpoint. If only incident flags
and final measurements are released, preserve that bounded endpoint use;
another such workbook does not identify the requested full clinical dynamics.

Record the answers, unresolved fields and a source-specific selection plan
before any separately authorized participant acquisition. If adequate paths
exist, freeze the observation/selection/stopping likelihood, alternative
assumptions, identification checks, joint uncertainty and evaluation plan before
fitting. Do not infer biological onset from detection, assume missing follow-up
means living unchanged, or convert visit changes directly to annual rates.

## Why SLIMM-T2D stays conditional

SLIMM's early assessment is partly weight-loss-triggered. Its nominal month
label is not verified exact elapsed time. A clinical dictionary must establish
actual clocks or justified windows, unique subject/visit keys, cross-file
medication linkage and released-subset selection. Visit-level medication use
alone does not establish start/stop dates or a treatment-free remission duration.
Death, last contact and withdrawal/loss coverage remain unverified. The separately
published `data/S2_readme.csv` explains omics/statistical output sheets rather
than resolving those clinical fields. No clinical file or whole repository ZIP
was fetched. If rights and observables become adequate, the bounded candidate is
a joint post-diagnosis observation distribution under its assigned interventions,
not an isolated food effect or a national transition rate.

## Reproducibility and scientific boundary

The [original receipt artifact](validation/public-longitudinal-admission-receipts-v1.json)
and [publication-field correction](validation/public-longitudinal-status-correction-v1.json)
pin the actual successful metadata, primary publication and separate
documentation acquisitions, with UTC times, URLs, media, byte sizes and SHA-256.
Every included successful cache was checked against its receipt before assembly.
Full source documents remain ignored and fetch-only. Metadata checksums are
provenance checks, not clinical validity or participant-data permission.
HTTP failures and approval chronology are retained separately from successful
pins. Earlier web inspection/search snippets exposed published results; these
are used sources, not reserved validation observations. No numerical outcome
intake, empirical arithmetic or fit occurred.

`uv run demeter data verify-packages --check-tracked` verifies the committed
appraisal/receipt artifacts offline. It does not reacquire source documents,
verify optional ignored caches, or grant record access. The
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md), likelihood,
evidence registry and scenario behavior are unchanged. This appraisal feeds
design inputs I-11/I-12 and formulation F-08 in the
[design registers](design/README.md); it activates no mechanism.

Requirements in #57, [#58](https://github.com/Crusonia/Demeter/issues/58),
[#1](https://github.com/Crusonia/Demeter/issues/1) and milestone
[#27](https://github.com/Crusonia/Demeter/issues/27) remain unresolved. Independent
prediction, U.S. transport, causal dietary dose/lag, clinical mortality and engine
activation are separate gates. Simulations remain validation-only; these source
leads support no healthcare-savings or value-chain investment conclusion.
