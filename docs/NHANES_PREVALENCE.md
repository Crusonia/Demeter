# Reproducible glycemic population evidence

This advances issue #1's baseline-prevalence work. It does **not** complete the
national T2D state mapping, longitudinal transition estimation, dietary-response
identification, or independent health holdout. Engine parameters and trajectories
remain validation-only.

## Sources and definitions

Four original CDC/NCHS NHANES 2017-March 2020 files are committed in
`data/sources/nhanes/2017-2020`: demographics, diabetes interview, glycohemoglobin,
and fasting glucose. Source URLs, retrieval times, original-byte hashes, and use
terms are in the colocated manifest. No network is needed to reconstruct the
aggregate bundle. All cutoffs, age groups, and reference estimates are registered
under `datasets.nhanes_glycemic_prevalence` in `evidence/parameters.yaml`.

The [NCHS report, Table 8](https://www.cdc.gov/nchs/data/nhsr/nhsr158-508.pdf)
defines the adult diabetes reconstruction. Adults 20+ are partitioned into
normoglycemia, survey-defined prediabetes, and diabetes of any type. Known
pregnancy at ages 20-44 is excluded. Complete records require an interpretable
diabetes interview and both laboratory measurements. Prior diabetes diagnosis
takes precedence over current low laboratory values. Refused/unknown responses
and missing laboratory values are never assigned to the healthy category.

Prediabetes uses the [NCHS glycemic definition](https://www.cdc.gov/nchs/data/nhsr/nhsr123-508.pdf):
below the diabetes thresholds, A1c at least 5.7% or fasting glucose at least
100 mg/dL. Diabetes uses self-reported diagnosis, A1c at least 6.5%, or fasting
glucose at least 126 mg/dL. These population survey classifications are not
confirmed clinical diagnoses. Normoglycemia does not establish overall metabolic
health, and the all-type diabetes observation cannot silently initialize T2D.

## Survey estimator and uncertainty

Use the [fasting-subsample weight WTSAFPRP](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_GLU.htm)
and the masked strata/PSUs in demographics. All positive-weight survey records
remain in the design, including adolescents, excluded pregnancies, and records
outside each age/sex domain. Complete-case domains determine the point estimates;
out-of-domain residuals are zero. This follows the
[CDC subgroup variance guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/varianceestimation.aspx).

For a binary state indicator Y and complete-case domain indicator D:

```
p = sum(w D Y) / sum(w D)
e_hi = sum_j w_hij D_hij (Y_hij - p) / sum(w D)
V(p) = sum_h [m_h / (m_h - 1)] sum_i (e_hi - mean_h(e))^2
```

Each domain reports standard errors and logit-t confidence intervals, using the
number of contributing PSUs minus strata for degrees of freedom. Singleton strata
fail; empty domains and boundary/zero-variance estimates have no manufactured
confidence interval. These intervals are not the published Korn-Graubard intervals
and do not imply that full NCHS reliability screening passed. The source warning
for diabetes in men 20-39 is preserved. Missingness counts and weighted fractions
are reported; there is no extra item-nonresponse correction.

The XPORT loader corrects the documented [pandas zero-decoding defect](https://github.com/pandas-dev/pandas/issues/30051)
by mapping exactly `2**-260` back to zero. It does not round arbitrary small values.
The official glucose codebook's zero and positive-weight record counts are tested.

## Verification and remaining mapping

The reconstruction matches all 12 published crude/age-specific diabetes cells by
sex at the report's displayed precision and their exact sample sizes. Unit tests
also check analytic survey-variance fixtures, classification boundaries,
missingness, source corruption, deterministic offline rebuilding, and CLI guards.
This is a same-source extraction cross-check, not an independent health holdout.

Derived floating-point results are serialized to 12 significant digits to remove
platform-dependent final-bit differences from BLAS and statistical libraries.
This is a storage convention, not a claim of measurement precision. Calculations
and published-target checks use full precision; raw source and evidence-definition
hashes remain exact. CI requires byte-identical reconstruction on all platforms.

Before using these observations in the engine, identify T2D separately, resolve
the IR-versus-prediabetes distinction, obtain pediatric and later-period evidence,
and document any single-age interpolation and transport assumptions. An explicit
observation model is needed to compare the current engine's states to survey
definitions. The bundle therefore remains `benchmark_only`.

```powershell
uv run demeter data verify-store
uv run demeter data rebuild-nhanes --destination outputs/nhanes-rebuilt
uv run demeter evidence population --output outputs/population-evidence.json
```
