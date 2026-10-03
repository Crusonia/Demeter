# NHANES 2021–2023 glycemic observations

This benchmark reconstructs the August 2021–August 2023 U.S. civilian
noninstitutionalized adult fasting subsample from four public CDC/NCHS files.
It supplements the [2017–March 2020 reconstruction](NHANES_PREVALENCE.md).
It does not replace that bundle, initialize the model or establish clinical
transition hazards. The scientific v0.1 release gate remains closed.

The design trace is I-01/I-07/I-11/I-12 → F-08 → T-01/T-05/T-08 in the
[design registers](design/README.md). The current health slice needs better
population observations before those observations can be mapped to latent
metabolic states. Any-type diabetes, survey prediabetes and normoglycemia are
observations; they are not automatically T2D, all insulin resistance or general
metabolic health.

## Reproduce it offline

From the repository root, after the [usual installation](GETTING_STARTED.md):

```powershell
uv run demeter evidence glycemic-2021-2023
uv run demeter evidence glycemic-2021-2023 --output outputs/glycemic-2021-2023.json
uv run python scripts/verify_nhanes_current.py
uv run demeter data verify-store
```

These commands also work in macOS/Linux shells. The first prints a compact
aggregate summary; the second saves the complete estimates and covariance.
Use a new output filename for each run. Output inside sources, code,
documentation or the evidence directory is refused, including a missing frozen
filename. Existing outputs and file aliases are never overwritten. The offline
reporter performs no downloads and exports no joined participant records.

The committed [source store](../data/sources/nhanes/2021-2023/manifest.json)
contains the original XPORT bytes and acquisition metadata. The
[protocol](validation/nhanes-2021-2023-intake-protocol-v1.json) was committed
before acquisition of the three new interview/laboratory files and before
statistical execution. DEMO_L was already used in the dietary bundle; its
original receipt and actual reuse time are both retained. Published outcomes
and codebooks were inspected before the protocol. This is used-source work,
not preregistration or an untouched holdout.

The [source admission receipt](validation/nhanes-2021-2023-source-admission-v1.json)
records byte pins separately from the
[aggregate reconstruction](validation/nhanes-2021-2023-glycemic-reconstruction-v1.json).
A new definition, source or implementation checksum requires explicit
admission; editing a local manifest alone cannot reseal the reporter.

The supported library replay API is
`demeter.data.nhanes_current_admission.report`. The CLI and strict verifier use
this guard. It independently pins the original source admission and frozen
aggregate, using the aggregate's original implementation hashes to verify
registry, repository and actual loaded code before invoking any v1 calculation
function. The original source store, calculation modules and report remain
byte-preserved. Their lower-level replay is a historical implementation, not
the supported admission API. This guard changes no report fields, observations
or registry definitions. Verification outputs must also be new files outside
`data`, `src`, `docs` and `evidence`.

The explicit acquisition script stages each attempt separately. It publishes
the requested destination only after all four components and the manifest pass
byte checks, using an atomic operation that refuses an existing target. A
failed attempt retains partial bytes and receipts in the reported attempt
directory; retry the same requested destination without deleting evidence.
Offline reconstruction does not invoke this script.

## Two denominators answer different questions

| View | Denominator | Interpretation |
| --- | --- | --- |
| Complete-case conditional categories | Eligible positive-fasting-weight adults with an interpretable interview and both finite positive assays | Glycemic shares among observed complete cases |
| Eligible-population complete partition | All eligible positive-fasting-weight adults in the domain | Includes an explicit unclassified share |
| Eligible-population compatible sets | Same eligible denominator | Seven disjoint nonempty sets of glycemic labels consistent with available observations |
| Compatible-category lower/upper bounds | Same eligible denominator | Definite versus possible membership, with sampling uncertainty of both endpoints |

A person reporting prior diabetes remains diabetes-compatible even if an assay
is missing. Under the inherited complete-case rule, that person is unclassified
in the complete partition and absent from the conditional denominator.
Missing interviews or assays never become normal observations.

Diagnosis takes precedence over low current laboratory values. Borderline
interview responses retain the inherited documented classification. Known
pregnancy at ages 20–44 is excluded; unknown or unavailable pregnancy is reported
in coverage. Age 80 is top-coded, not exact age. Adults, subgroups and sex domains
overlap and must not be added together as independent populations.

The registered cutoffs are inherited unchanged: A1c 5.7%/6.5%, fasting glucose
100/126 mg/dL, and age groups 20+, 20–39, 40–59 and 60+. These survey definitions
do not confirm an individual clinical diagnosis.

## Weights and dependent uncertainty

The source fasting weight is **WTSAF2YR**, as documented in
[GLU_L](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GLU_L.htm).
WTPH2YR is the phlebotomy weight and is not substituted into this combined
A1c/glucose/interview estimator. No historical WTSAFPRP field exists in the
current source. The adapter copies WTSAF2YR into the unchanged pure estimator's
internal working column and records that mapping explicitly; physical or
conflicting historical weight fields are refused.

All positive-weight design rows remain present, including out-of-domain
adolescents, excluded pregnancies and PSUs with zero domain contribution.
Masked stratum/PSU variables determine the Taylor variance. Empty domains are
unavailable rather than zero, and singleton full-design strata are refused.

For coordinate k, the weighted ratio and PSU influence totals are:

```text
p[k] = sum(w * D[k] * Y[k]) / sum(w * D[k])
T[h,j,k] = sum_in_PSU(w * D[k] * (Y[k] - p[k])) / sum(w * D[k])
V = sum_h m[h]/(m[h]-1) * sum_j (T[h,j] - mean_h(T)) (T[h,j] - mean_h(T))'
```

Twelve age/sex domains are evaluated under both denominator families in one
calculation. A fixed projection selects 132 eligible coordinates and 60
complete-case coordinates: the three glycemic labels and diagnosed/undiagnosed
diabetes subdivisions. Their **192-coordinate covariance** retains cross-family,
cross-category and cross-domain dependence. Logical category-bound endpoints
use a further fixed projection.

Partition closure and finite survey support make singular covariance expected.
No ridge, clipping, pseudo-inverse, independent draws or fitted sampling
distribution is introduced. Marginal logit-t intervals differ from published
NCHS intervals; covariance does not establish simultaneous confidence coverage.
Twelve significant digits is a cross-platform storage convention, not
measurement precision.

## Source checks and remaining limits

The first frozen reconstruction passes all 18 sample-size and displayed-point
checks. Its complete-case adult denominator is 2,938; the eligible denominator
is 2,940, retaining two unclassified participants. Eighteen known pregnancies
are excluded. The reconstructed crude any-type diabetes share is about 15.8%
among complete cases, matching the published display. These are same-source
population observations, not model predictions or independently validated effects.

The source audit verifies byte identity, selected-field schema, linkage and
implementation integrity. It does not reproduce every codebook frequency table.
In particular, missing-weight counts in the joined demographic frame include
people outside the released glucose component; they must not be interpreted as
missing fasting weights among that component's participants.

Eighteen crude total/diagnosed/undiagnosed diabetes cells in
[NCHS Data Brief 516, Tables 1–2](https://www.cdc.gov/nchs/products/databriefs/db516.htm)
provide same-source checks of sample sizes and displayed point estimates.
Published confidence limits and standard errors remain attributed source
values. The half-decimal display check is a formatting test, not a clinical
acceptance tolerance. A discrepancy is reported and investigated; definitions,
weights or exclusions are not tuned to eliminate it. Age-adjusted values are
not substituted for crude estimates.

[GHB_L](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GHB_L.htm)
documents a within-cycle primary instrument change from Tosoh G8 to Bio-Rad
D-100 and a secondary instrumentation change, with method/site unchanged.
No participant-specific instrument assignment or correction is invented.
GLU_L documents no new adjustment needed for these released glucose values;
historical regression corrections are not reapplied.

Sampling covariance excludes assay/measurement error, missingness bias, unknown
pregnancy, latent-state definitions and temporal/population transport. The
complete-case benchmark does not establish representativeness after item
nonresponse. Full NCHS reliability screening is not implemented, and single
assays do not confirm diabetes. Source agreement is not an independent health
holdout or validation of a dietary effect.

Meaningful tests cover analytic covariance, scalar parity, denominator changes,
history priority, exact cutoffs, full-design preservation, bounds projection,
closure/singularity, source corruption before parsing, malformed linkage,
cycle/weight confusion, offline replay, and unchanged annual-model outputs.

Original CDC/NCHS files remain separate from Demeter transformations and are
available free from CDC. The [NCHS data-user agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html)
and [repository notices](../data/NOTICE.md) apply. No identification, linkage
to identifiable records or joined person-level export is performed.
