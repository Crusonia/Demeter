# Building Demeter with public evidence

The [Stanford iPOP schema appraisal](IPOP_SOURCE_COVERAGE.md) now verifies eight
metadata surfaces, producer linkage/clock operations and the publication's A1c
and glucose measure names. It pins the source bytes and preserved acquisition
failures separately from inspected content. Subsequent review of Zheng et al.
(2022) establishes public provenance for the named derivative release. A narrow linked
laboratory-panel intake can proceed under frozen, explicit measurement/clock
assumptions; upstream rawness, specimen association and actual record coverage
remain to be checked. No clinical fit or national calibration has been admitted.

The [Whitehall II endpoint package](WHITEHALL_ENDPOINT.md) now reproduces two
published FPG follow-up labels and evaluates an explicit conditional binomial
working likelihood, with a descriptive-only alternative. This advances the
observation layer while leaving clinical transition identification, diet effects,
U.S. transport and external scientific evaluation unresolved. Its design was
frozen before planned selected-cell capture, after prior/incidental result exposure.

The [PREVIEW endpoint reproduction](PREVIEW_ENDPOINT_AUDIT.md) adds published
normal-glucose snapshots under a frozen used-source specification. It keeps
available-endpoint contrasts, adjusted trial estimates, and deterministic
missing-label envelopes separate, while retaining source disagreements. It
advances source appraisal for #57/#58; linked clinical transitions, dose/lag
identification, independent validation and national transport remain open.

The [TOTUM63 source-row audit](TOTUM_SOURCE_ADEQUACY.md) now checks actual public
glucose cells under a selection committed before numerical intake. It examines
raw-cell and layout coverage without a clinical effect calculation. Public
access, record-unit semantics and sufficient clinical histories are separate
requirements; unresolved pairing, treatment, death and timing still block a fit.

The maintainer selected the public-source route on September 29, 2026. We can
build useful, reproducible pieces without waiting for institutional data access.
Each source has a specific job; combining public studies does not automatically
identify a national causal model. This feeds [#56](https://github.com/Crusonia/Demeter/issues/56),
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58).

## Work in this order

| Priority | Public evidence | What it can establish | Next deliverable |
| --- | --- | --- | --- |
| 1 | [Chen public cohort](https://doi.org/10.5061/dryad.ft8750v), CC0 data | Source-specific baseline/final glucose and recorded incident diabetes | [Timing audit complete](CHEN_TIMING_AUDIT.md), source disagreements retained; keep descriptive benchmarks and seek compatible observations before a likelihood fit |
| 1a | [Stanford iPOP public derivative](IPOP_SOURCE_COVERAGE.md) | Author-declared public provenance and documented measurement/linkage surface for repeated native-cohort laboratory observations | Freeze a narrow linked-panel intake with explicit assay/relative-day assumptions; assess coverage and alternatives before fitting; do not substitute class/context labels for glycemic history |
| 2 | Archived NHANES and NCHS linked mortality | U.S. observed glycemic categories and baseline-category mortality prediction | Carry explicit unknown/type categories forward; assess supported initialization and conditional mortality, keeping the frozen prediction evaluation separate |
| 3 | Public aggregate longitudinal studies, including corrected ARIC and CARRS tables | External comparisons of progression/recovery under each study's definitions | Record intervals, competing-event handling and covariance availability; test whether any package identifies a compatible joint model |
| 4 | [Hall intake reproduction](FOOD_INTAKE_REPRODUCTION.md), [corrected Reus assessment](REUS_DIABETES_PATHWAY.md) and public trial protocols | Study-compatible food intervention endpoints and explicit source-to-model limits | Define a compatible observation contract, appraise an independent source, and retain null alternatives and overlapping-effect uncertainty before fitting a disease bridge |

U.S. mortality/population archives, observation mapping and the Hall analysis
already exist. The executable Chen intake/timing audit and Reus reported-result
reproduction now exist. Joint hazard identification and independent pathway
evaluation remain research work, not completed calibration. Controlled ARIC/DPP access stays
optional; no applicant, agreement or outreach is needed for this public work.

## First public cohort: executable intake

The [protocol](rfcs/RFC-57-public-cohort-intake.md) was committed as `d07208a`
before participant-outcome aggregation. Published study results were already
known. The [aggregate result](validation/issue-57-public-cohort.json) reproduces
the released participant and sex totals and the recorded incident-diabetes total.

It also retains an actual failed check: the released follow-up column has a
median of approximately **2.99 years**, versus **3.1 years** in the
[original article](https://doi.org/10.1136/bmjopen-2018-021768). The published value
is not substituted into the data, and the tolerance is not relaxed after seeing
the result. The command emits the report and exits **1** for that discrepancy.
This is a completed source audit with an unresolved source issue, not a software
test failure or an accepted calibration input.

Column T marks reported diagnosis with one but has no recorded zeros. Its blanks
remain unknown. Positive evidence agrees with column U; treating blanks as no
diagnosis reconstructs all recorded endpoint flags, but that conditional agreement
does not independently document blank coding. Missing final glucose is preserved.
No annual risk, reversal hazard, remission rate or dietary effect is estimated.

The registry contains all analysis constants. The source rights inventory records
the original dataset's CC0 dedication separately from article rights. The workbook
is fetch-only because it is a large microdata file; this does not require an
institution or a data-use application. Small aggregate data, protocol, receipts
and transforms live in the repository. Ordinary tests need no network or workbook.

### Reproduce on Windows

From the repository root after `uv sync --locked`:

```powershell
New-Item -ItemType Directory -Force data/raw/clinical | Out-Null
Invoke-WebRequest 'https://zenodo.org/api/records/4997196/files/RC%20Health%20Care%20Data-20180820.xlsx/content' -OutFile data/raw/clinical/chen2018.xlsx
uv run demeter evidence public-cohort --workbook data/raw/clinical/chen2018.xlsx --output outputs/chen-intake.json
```

### Reproduce on macOS or Linux

```bash
mkdir -p data/raw/clinical
curl --fail --location 'https://zenodo.org/api/records/4997196/files/RC%20Health%20Care%20Data-20180820.xlsx/content' --output data/raw/clinical/chen2018.xlsx
uv run demeter evidence public-cohort --workbook data/raw/clinical/chen2018.xlsx --output outputs/chen-intake.json
```

The analyzer checks exact bytes before opening the workbook, never recalculates
formulas, and exports no person-level rows. Preserve an existing matching download;
do not overwrite it with a changed upstream version. Downloads are optional and
separate from offline simulation. The current audit's exit 1 is expected as above.

## New aggregate-source appraisal

[Narayan et al., CARRS (2024)](https://doi.org/10.2337/dc23-1514) publishes fitted
annual probabilities for separate impaired-fasting-glucose and glucose-tolerance
pathways. It is a useful comparator, not a ready national hazard set: endpoint
probabilities differ from generator rates, subgroup estimates do not supply joint
covariance, and the reported three-state models do not supply competing-death
transitions. Inspection also found a table row that does not sum to one within
its displayed rounding precision. Preserve that discrepancy pending reconciliation.
The article's educational/nonprofit reuse condition is distinct from open data;
no article or underlying CARRS records are redistributed here.

[Zhang et al. (2022)](https://doi.org/10.1371/journal.pmed.1004045) is a relevant
Hong Kong/CHARLS model comparator, but its primary formulation assumes no
prediabetes reversion. It cannot supply the missing recovery mechanism by itself.
An openly licensed article also does not make its underlying clinical records an
unrestricted public download. Neither study activates a Demeter parameter.

## What a public-data result must earn

The [public longitudinal data requirements](PUBLIC_LONGITUDINAL_DATA_REQUIREMENTS.md)
turn the clinical observation contract into a contributor checklist and record
the October 1 bounded source search. Public access and sufficient observations
remain separate checks; no new clinical data or estimates were admitted.

The [DPP observation adapter](DPP_OBSERVATION_ADAPTER.md) adds a strict normalized
record contract and synthetic aggregate demonstration. Its four source receipts
cover public documentation, not public participant records. It keeps source years,
relative days and grouped periods separate and preserves diagnosis/confirmation,
missing tests, treatment, death and distinct censoring observations. This supports
the next source-field coverage review; clinical likelihood, identification and
permitted-record intake remain unresolved.

The [DPP coverage matrix](DPP_SOURCE_COVERAGE.md) completes the bounded
public-document appraisal: exact fields and recall windows, excluded dates,
source-version discrepancies and absent actual coverage remain distinct. The
current catalog makes participant records available for request; no request was
made. Prioritize compatible unrestricted observations or sufficient published
statistics for clinical estimation. More blank forms do not resolve missing
histories, diagnosis timing or an isolated dietary pathway.

The [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) specifies
the source review and likelihood requirements before a clinical fit.
The [Reus assessment](REUS_DIABETES_PATHWAY.md) reproduces all six frozen overall
HR/CI cells from the separate original/correction reports. Its synthetic checks
show how identical one-year endpoints can coexist with different recovery and
progression hazards, and how dose/coefficient or lag/coefficient pairs can be
ambiguous in the implemented response. These checks never use the trial HRs as
inputs and do not establish identification of the trial's adjusted Cox likelihood.
The full XML articles remain fetch-only. #58 stays open: source reproduction
does not establish the missing clinical transitions, dose, lag or U.S. transport.

Before fitting: pin the source version and definitions; resolve material coding
and timing conflicts; specify the estimand, observation process and likelihood;
show which parameters are identifiable; freeze an evaluation partition where
available. After fitting: report joint uncertainty, failed predictions, supported
populations and transport assumptions. The current health model remains
validation-only until the scientific acceptance criteria are met.
