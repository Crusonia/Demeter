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
