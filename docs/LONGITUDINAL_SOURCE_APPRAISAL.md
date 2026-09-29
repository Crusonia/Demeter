# Longitudinal source appraisal for issue #57

Assessment date: September 29, 2026 (UTC). Codex-assisted source inspection;
external expert review pending. Supports [RFC-57](rfcs/RFC-57-longitudinal-identification.md).

## Decision

Two publicly released workbooks were acquired and checked against the publishers'
file identities. Neither release supplies the complete observation package needed
to estimate Demeter's progression, reversal, treatment and competing-death dynamics.
No transition rate was fitted or promoted to the evidence registry or engine.

The Chinese release contains baseline and final fasting glucose, so it remains a
candidate for a narrower, explicitly conditional analysis. The Japanese release
has baseline glycemia and an incident-diabetes endpoint, with no follow-up glycemic
measurements. It cannot directly measure glycemic regression. These conclusions
concern the released workbooks, not everything collected by the original studies.
They do not establish that no suitable public cohort exists.

This is an intake decision, not a failed numerical fit. The inspection read
workbook structure, headers and row counts; it did not extract participant-level
outcomes, execute formulas, estimate effects or choose a validation split.
Published study outcomes were already known. Any future protocol must preserve
that chronology rather than claiming the studies were untouched evidence.

## Source identities and access

| Release | Primary records | Verified workbook |
| --- | --- | --- |
| Chen et al., 2018 | [Dryad dataset](https://doi.org/10.5061/dryad.ft8750v), [original study](https://doi.org/10.1136/bmjopen-2018-021768), [Zenodo copy](https://zenodo.org/records/4997196) | `RC Health Care Data-20180820.xlsx`; sheet `RC`; 25 columns, 211,833 data rows |
| Okamura et al., 2019 data release | [Dryad dataset](https://doi.org/10.5061/dryad.8q0p192), [original study](https://doi.org/10.1038/s41366-018-0076-3), [Zenodo copy](https://zenodo.org/records/4996032) | `Data set Int J Obesity.xlsx`; sheet `Sheet 1`; 31 columns, 15,464 data rows |

The publication dates refer to the data releases. The Okamura article appeared
online in 2018 and in the January 2019 journal issue. Record counts above describe
workbook rows, not a newly checked analysis cohort or complete-case denominator.

Dryad's [Chen file metadata](https://datadryad.org/api/v2/versions/22783/files)
and [Okamura file metadata](https://datadryad.org/api/v2/versions/22266/files)
provide the filenames, sizes and MD5 digests. The corresponding dataset metadata
records license `CC0-1.0`; the Zenodo records identify the same DOIs, `cc-zero`
license and Dryad community. Downloaded bytes match both repositories' sizes and
MD5 values. SHA-256 was also calculated locally and is pinned below.

| Receipt field | Chen | Okamura |
| --- | --- | --- |
| Dryad file ID | 78961 | 76808 |
| Bytes | 28,340,131 | 3,255,571 |
| MD5 | `b468cc3704b11ba1bd21532451fe2856` | `47edfb147078657a0eecfff7f9364532` |
| SHA-256 | `ffd341a1a91ac65585b9fba70847a2681f5671a6035d9cfbf92e50795d74fbf6` | `671359aea2019c848f969395f88e57f888eaba8463ea0351bcda8f1c947f5523` |
| Retrieved UTC | 2026-09-29T04:54:40.667548+00:00 | 2026-09-29T04:47:15.663200+00:00 |
| Download | [Published file](https://zenodo.org/api/records/4997196/files/RC%20Health%20Care%20Data-20180820.xlsx/content) | [Published file](https://zenodo.org/api/records/4996032/files/Data%20set%20Int%20J%20Obesity.xlsx/content) |

Direct Dryad file requests returned HTTP 403 in this environment. The open Zenodo
copies were downloaded through their public record links; no account, access
agreement or restricted-access credential was used. Searching Zenodo for the DOI
suffix did not find the Chen record, while searching its filename or title did.
An empty search result was not treated as evidence of unavailability.

Original bytes remain in ignored local storage. This PR distributes the appraisal
and reproducible inspection instructions, not participant records or a new model
dataset. No workbook is required for ordinary simulation or the offline test suite.
These structural counts and file identities are provenance, not clinical parameters.

## What the releases actually contain

| Intake requirement | Chen release | Okamura release |
| --- | --- | --- |
| Age and sex | `RC!B1:C1` | `Sheet 1!B1:C1` |
| Baseline glycemia | Fasting glucose, `RC!J1`, mmol/L | HbA1c, `W1:X1`; fasting glucose, `AA1:AB1`, with alternate units |
| Later glycemia | Final-visit fasting glucose, `RC!S1`, mmol/L | No follow-up glycemic measurement column |
| Diabetes outcome/history | Two distinct fields at `RC!T1:U1`: diagnosed during follow-up and diabetes censor/event indicator | Incident DM flag, `Sheet 1!AE1` |
| Timing | One follow-up duration, `RC!V1`, years | One follow-up duration, `Sheet 1!K1`, days |
| Visit-by-visit measurement series | Not present in this workbook | Not present in this workbook |
| Medication starts/stops and sustained control | Not present in the header schema | Not present in the header schema |
| Death time and cause of follow-up termination | No explicit death or withdrawal-reason field | No explicit death or withdrawal-reason field |
| Diet or randomized dietary assignment | No such field | No such field |

Both releases also contain baseline anthropometric, biochemical and behavioral
covariates. These are observational cohorts, not dietary intervention trials.
Absence above means no corresponding column in the inspected release; it is not
a claim that the original investigators never collected that information.

### Chen: two observations do not mean two known transition times

The [primary dataset description](https://doi.org/10.5061/dryad.ft8750v) identifies
adult Chinese health-screening participants without baseline diabetes. It states
that follow-up ends at diabetes diagnosis or the final visit. The underlying
study's repeated visits are not all retained as measurements in the workbook.

The two diabetes fields must not be silently treated as synonyms. Their exact
event coding and the alignment of final glucose with the reported follow-up time
require a source-backed mapping before estimation. A final low glucose value is
an observed endpoint; its measurement date does not establish when improvement
first occurred or whether it persisted. Baseline diabetes exclusion and follow-up
termination at diagnosis provide no post-diabetes remission trajectory.

Two-time panel data can inform a restricted transition model under specified
assumptions. The objection is not that only fully observed transition times are
usable. A Chen analysis would first need to specify the observed endpoint and
censoring mechanism, account for unobserved intermediate transitions, examine
identifiability and selection, and justify any assumptions about death and
treatment. An apparently precise fit under those assumptions would not by itself
validate every engine hazard or transport it to the U.S. population.

### Okamura: incidence is not reversal

The released fields provide baseline glucose/HbA1c, follow-up duration and an
incident-diabetes indicator. There is no later glucose measurement with which to
observe regression to a lower glycemic category. Baseline-group incidence cannot
separately determine all current-state progression and reversal hazards.

The workbook contains formulas, including derived columns. No formula was
executed or recalculated. This structural appraisal does not verify their results,
the duration's event/censoring semantics, every original inclusion rule or diabetes
type ascertainment. The source title alone is not a validated type-classification
algorithm. Those questions remain required for any incidence-only reuse.

## Consequences for model design

| Proposed use | Disposition |
| --- | --- |
| Reproduce a source-specific incident-diabetes benchmark | Possible candidate; first resolve endpoint/time definitions, selection and analysis protocol |
| Estimate a restricted baseline-to-final glycemic model from Chen | Candidate only; define assumptions and test identifiability before fitting; preserve unobserved death/treatment limitations |
| Estimate diabetes remission or relapse after remission | Unsupported by these released histories |
| Estimate state-specific competing mortality jointly with transitions | Unsupported without additional compatible event evidence or explicit, separately supported constraints |
| Replace national initial-state proportions | Unsupported; cohort selection and population/time transport are unresolved |
| Identify a dietary causal effect | Unsupported; neither release identifies the required dietary intervention |

These dispositions preserve competing explanations and do not substitute a
narrower incidence benchmark for completion of #57. Registry parameters,
equations, scenarios and uncertainty distributions are unchanged. The health
model remains validation-only.

## The next useful data package

Prioritize a permitted release of repeated observations from ARIC, DPP/DPPOS or
another cohort that passes [RFC-57's intake contract](rfcs/RFC-57-longitudinal-identification.md#minimum-useful-intake-contract).
The needed addition is not another paper's hazard ratio. It is an analysis package
with:

- Individual visit intervals and repeated glucose/HbA1c measurements, assay units,
  diagnostic history and documented missingness.
- Treatment and intervention timing, including enough follow-up after diabetes
  onset to assess any proposed improvement/remission state.
- Deaths, last known contact and reasons for follow-up termination, or an explicit
  account of which competing-event estimands cannot be identified.
- Population/selection documentation, authorized use and publication terms, and
  fields permitting a validation partition to be frozen before model selection.

These are selection criteria, not a claim that every named cohort supplies every
field. ARIC/DPP access remains unapproved in this work; no application, agreement
or message to investigators has been sent. A suitable published aggregate package
remains an alternative if its intervals, joint transitions, deaths, denominators
and uncertainty identify the specified estimands. #57 remains open.

### ARIC: a concrete access candidate

The current [BioLINCC ARIC listing](https://biolincc.nhlbi.nih.gov/studies/aric/)
(accession `HLB00020026a`, dataset update August 3, 2026) offers examination visits
1-10, annual follow-up and mortality follow-up through 2023. Its consent section
prohibits commercial use. Access requires a registered request; Demeter's intended
use and any downstream publication of derived materials must be assessed against
the actual agreement before selecting this route. Open documentation is not data
access approval or permission to use these records for commercial analysis.

The public [2026 data dictionary](https://biolincc.nhlbi.nih.gov/media/studies/aric/data_dictionary/ARIC_2026a.pdf)
provides the following request targets. Page numbers are PDF pages, checked against
rendered tables. These are candidate mappings, not validated joins or complete data.

| Target | Documented fields and locator | Remaining check |
| --- | --- | --- |
| Repeated labs | `v1_v10_longlab_240508.sas7bdat`, pp. 422-423: `ID_C`, `VISIT`, `FAST08`, `FAST12`, `FASTING_TIME`, `VALUE_GLU`, `VALUE_HBA1C`, and corresponding assay-method fields | Cohort linkage, fasting validity, units, assay comparability and missing visits |
| Collection timing | Same file, p. 427: `COLLECT_DATE_GLU_FOLLOWUPDAYS`, `COLLECT_DATE_HBA1C_FOLLOWUPDAYS` | Use collection timing; do not silently substitute result dates |
| Mortality and last contact | `status71.sas7bdat`, p. 128: `DATEOFDEATH_FOLLOWUPDAYS`, `LASTFUINTERVIEWDATE_FOLLOWUPDAYS` | This file has an earlier cutoff; select event/contact files matching the eventual lab window |
| Diagnosis and treatment | Annual follow-up composite, p. 4; `mcups1.sas7bdat`, pp. 24-25; visit-specific medication forms | Obtain codebooks and harmonize histories; these labels do not establish medication cessation or sustained remission |

Dictionary receipt: 11,761,433 bytes; SHA-256
`e688977e8b8ceea16086ce0d045d6828621c3a329d0551e81893f1886e0748b0`;
retrieved `2026-09-29T04:59:50.675537+00:00`. Only public documentation was
downloaded. No ARIC participant data were accessed. The next access decision needs
a responsible research applicant, an eligible purpose and permitted output terms;
the dictionary alone does not resolve those requirements.

### NHIS: public follow-up measures diagnosis reports, not glycemic recovery

The [2020 NHIS release](https://www.cdc.gov/nchs/nhis/documentation/2020-nhis.html)
includes a public linkage file for adults interviewed in both 2019 and 2020.
Its [longitudinal codebook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2020/adultlong-codebook.pdf)
contains household linkage keys and `WTSA_L`, not the health observations
themselves. The [survey description](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2020/srvydesc-508.pdf),
pp. 54-57, joins `adult19`, `adult20` and `adultlong20` through `HHX_2019` and
`HHX_2020`. Longitudinal analysis uses `WTSA_L` and the **2019** `PSTRAT`/`PPSU`
variance design. Annual `WTFA_A` and pooled-sample `WTSA_P` serve different purposes;
they cannot be substituted for the longitudinal weight.

The actual [2019 adult codebook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2019/adult-codebook.pdf)
and [2020 adult codebook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2020/adult-codebook.pdf)
give the following observation contract. Page references are PDF pages.

| Field | 2019 / 2020 pages | Meaning and implication |
| --- | --- | --- |
| `PREDIB_A` | 117 / 118 | Whether a professional ever diagnosed prediabetes; not current laboratory-defined prediabetes |
| `DIBEV_A` | 119 / 120 | Whether a professional ever diagnosed diabetes, excluding the specified gestational/prediabetes responses; not current glycemic control |
| `DIBTYPE_A` | 127 / 128 | Self-reported type among respondents reporting diabetes; other type, refusal and unknown remain separate |
| `DIBPILL_A`, `DIBINS_A` | 122-123 / 123-124 | Current pills/insulin among people reporting prediabetes or diabetes; not complete treatment start/stop histories |
| `DIBAGETC_A`, `DIFYRSTC_A` | 2020: 121-122 | Coarsened diagnosis age/duration, with top-coding and missing codes; not exact disease-onset times |

A yes-to-no change in an **ever-diagnosed** answer is inconsistent reporting,
correction or another observation issue; it does not identify remission. A
no-to-yes change concerns a newly reported diagnosis, which can follow biological
onset by an unknown interval. The two questionnaires do not supply repeated
measured fasting glucose/HbA1c with which to identify glycemic reversal. Current
medication answers do not resolve that missing measurement or establish sustained
control off medication. These are interpretation limits, not estimated error rates.

The survey description, pp. 16-17, also records telephone/contact eligibility,
exclusion of proxy interviews from followback, and termination when death or
incapacity is learned. The [weighting and bias report](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2020/nonresponse-report-508.pdf),
pp. 7-11 and 24-25, describes weights targeting the original population and residual
selection: the reinterview sample consists of survivors. Weight adjustment does
not restore their missing death events or make this a complete competing-risk
history. Pandemic-period changes in care, detection and interview mode also
prevent treating these observations as an ordinary year of untreated biology.

For #56, NHIS remains a candidate **diagnosed-type observation benchmark**. CDC's
[national diabetes methods](https://usdss.cdc.gov/diabetes/data/socrata/National_Burden_Magnitude_methods.html)
combine reported type with current insulin use. That operational algorithm does
not clinically confirm each person's type or classify undiagnosed diabetes.
It must not be silently applied to NHANES participants, whose type is unmeasured,
or used to allocate all diabetes to T2D. Combining the surveys requires a separate
measurement/transport model, compatible populations and joint uncertainty.

Disposition: do not fit Demeter's progression/reversal hazards from these answers.
An NHIS diagnosis-report analysis would answer a narrower question and would not
close #56 or #57. Only public documentation was downloaded and inspected here;
no participant records were linked, no prevalence was estimated, and no model
input was adopted. Any future record analysis must follow the
[NCHS public-use agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html),
including statistical use and no attempted identification. Public availability
does not erase those conditions.

The downloaded documentation is pinned below. The three 2020 diagnosis/type
pages, survey join instructions and survivor-selection discussion were also
checked as rendered pages. Receipts and PDFs remain in ignored local research
storage; no source PDF is required by the simulation or redistributed in this PR.
These hashes and locators are provenance, not new clinical parameters.

| Document | Bytes | SHA-256 | Retrieved UTC on 2026-09-29 |
| --- | --- | --- | --- |
| 2019 adult codebook | 3,214,744 | `b110ac796cd223a6ebf8de5f70ab4138eed0069164253105f1b6579351e2d710` | 05:34:50.878216 |
| 2020 adult codebook | 2,118,199 | `2fa74451239e279d1c69ebed590b42719255f16790072fc448e99e1f68efd324` | 05:32:57.305332 |
| 2020 longitudinal codebook | 119,312 | `1dc189f3fb4ce52c1efab87ad99276352a6e3100786ac0c9c7093dc494fea9d0` | 05:32:44.800330 |
| 2020 survey description | 2,764,536 | `9d707334254ed422103bd1513df88d28fb67a61a1f271e7c6f38e61c341e28f7` | 05:33:00.173500 |
| 2020 weighting/bias report | 563,612 | `a61d89cae88950dcf08e599147e0417ac35721ab611213eb382dcf8ecd27b396` | 05:32:47.246144 |

### Research-access brief for the maintainer

This is an unsubmitted research brief, not a claim of institutional approval or
permission to obtain restricted records. It makes the next access decision
concrete without replacing the full model objective with a diagnosis benchmark.

- **Research question:** estimate supported-population movement between measured
  glycemic categories while retaining diagnosis history, treatment, death and
  observation timing; evaluate what can be transported to Demeter's target
  population. Food effects require their own intervention evidence.
- **Candidate package:** ARIC's visit-level lab and collection-time fields,
  diagnosis/medication histories and matching mortality/last-contact release
  identified above. The first intake must verify units, consent coverage and
  joins before selecting observations or freezing a fit/validation protocol.
- **Analysis:** follow RFC-57's competing-transition and observation-model
  alternatives, identifiability checks, joint uncertainty and independent
  prediction. Do not claim a nationally applicable rate from a selected cohort.
- **Intended public outputs:** Demeter-written analysis code, documented
  assumptions, approved aggregate estimates with joint uncertainty and validation
  reports. Participant records and restricted extracts would remain outside the
  public repository. Permission to distribute each derived output must be
  checked against the actual agreement; it is not inferred from aggregation.
- **Inputs still needed from a responsible researcher:** principal investigator
  and institution, intended research and downstream uses, institutional review
  documentation, permitted storage/access arrangements and an authorized signing
  official. No names, approvals, commitments or signatures are supplied by Codex.
- **Decision before requesting access:** ARIC's noncommercial condition must be
  compatible with the proposed research and outputs. If unrestricted commercial
  reuse is required, this release is not an assumed solution; an alternative
  permitted package or sufficient published aggregate evidence is needed.

The [BioLINCC FAQ](https://biolincc.nhlbi.nih.gov/faq/) describes the application,
institutional review and signed distribution agreement. No application, account,
agreement or investigator message has been initiated. An approved research
partner/package would enable the next intake; the current public-source appraisal
does not identify all required transition, mortality and dietary parameters.

## Repeat the structural inspection

Download the two pinned files using the links above and keep them outside tracked
source directories. In the repository root, save the following as
`outputs/inspect_longitudinal_headers.py`, replacing the two local paths if needed.
It reads bytes and header cells only, fails before workbook parsing on a checksum
mismatch, and prints no participant records. `data_only=False` avoids presenting
cached formula results as verified measurements.

```python
from hashlib import sha256
from pathlib import Path

from openpyxl import load_workbook

sources = (
    (
        Path("outputs/longitudinal-candidates/chen2018.xlsx"),
        "ffd341a1a91ac65585b9fba70847a2681f5671a6035d9cfbf92e50795d74fbf6",
        28340131,
    ),
    (
        Path("outputs/longitudinal-candidates/okamura2019.xlsx"),
        "671359aea2019c848f969395f88e57f888eaba8463ea0351bcda8f1c947f5523",
        3255571,
    ),
)
for path, expected_hash, expected_bytes in sources:
    raw = path.read_bytes()
    if len(raw) != expected_bytes or sha256(raw).hexdigest() != expected_hash:
        raise ValueError(f"Source identity mismatch: {path.name}")
    workbook = load_workbook(path, read_only=True, data_only=False)
    try:
        for sheet in workbook:
            print(path.name, sheet.title, sheet.calculate_dimension())
            for cell in next(sheet.iter_rows(min_row=1, max_row=1)):
                print(cell.coordinate, cell.value)
    finally:
        workbook.close()
```

Run on Windows, macOS or Linux:

```text
uv run python -X utf8 outputs/inspect_longitudinal_headers.py
```

The expected sheet dimensions are `A1:Y211834` and `A1:AE15465`, respectively.
Dimensions describe the source's declared used range. The original inspection
also counted worksheet row elements; neither check estimates completeness or
independent participants. A future clinical extraction needs its own preread
protocol, source mapping, evidence records and meaningful validation tests.
