# Joint sampling uncertainty for observed glycemic categories

Existing NHANES summaries provide point estimates and marginal intervals.
Those estimates share respondents and constrained totals. This optional report
calculates their joint survey covariance, including unknown observations and
overlapping age/sex domains, before proposed clinical-state initialization.

For a newcomer: category fractions still total one when estimates vary.
Covariance records their dependence. It does not turn missing observations
into known health states or establish a causal change in disease.

## Reproduce offline on Windows, macOS or Linux

After the existing setup (`uv sync --locked`), use a new output filename:

```text
uv run demeter evidence glycemic-uncertainty --output outputs/glycemic-uncertainty.json
uv run demeter data verify-packages --check-tracked
```

The command verifies the frozen protocol, existing definitions/classifiers and
four archived NHANES files before calculation. It exports aggregates only and
refuses to overwrite an existing output, including aliases to inputs. Use a
fresh filename on rerun. Without `--output`, it emits the full JSON report.

The [RFC](rfcs/RFC-56-joint-glycemic-uncertainty.md) and
[protocol](validation/joint-glycemic-uncertainty-protocol-v1.json) precede new
covariance execution. Source and original estimates were already inspected:
this is used-source analysis, not preregistration or an untouched holdout.

The committed [aggregate report](validation/joint-glycemic-uncertainty.json)
contains 132 coordinates across 12 age/sex domains. The
[before/after proof](validation/joint-glycemic-uncertainty-before-after.json)
reproduces that report and verifies unchanged prior parameters, datasets,
clinical source records, four canonical scenarios, fixed-seed uncertainty
outputs and scientific blockers. To reproduce the report check separately:

```text
uv run python scripts/verify_joint_glycemic_uncertainty.py
```

## Calculation and interpretation

Complete-case categories are normoglycemia, prediabetes, diabetes of any type
and unclassified. The denominator retains all eligible weight. Separately,
partial observations use the seven nonempty compatible-category sets. These
set patterns are disjoint; individual category-compatibility indicators overlap.

Both partitions and all registered age/sex domains form one vector. Proportions
are linearized as survey ratios, summed within masked PSUs, centered within
masked strata and combined through corrected outer products. All positive-weight
design rows remain, including zero-domain contributions. This follows
[CDC Taylor and domain guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/varianceestimation.aspx)
and the [official survey covariance calculation](https://stat.ethz.ch/CRAN/web/packages/survey/refman/survey.html#svyCprod).
It is a Python calculation; no independent R execution is claimed.

Lower membership uses the singleton pattern; upper membership sums patterns
containing that category. A fixed linear projection calculates endpoint
covariance, retaining dependence between categories and domains. Membership
ranges describe unresolved category information; sampling covariance describes
survey variability of their endpoints. Neither gives a point allocation inside
a range or a simultaneous confidence band.

Covariance units are fraction squared. Partition closure and limited survey
support imply singularity; no ridge, clipping or sampling distribution is
introduced. Empty domains remain unavailable; singleton full-design strata
fail rather than receiving invented variance. Existing marginal points, bounds,
standard errors, intervals and clinical thresholds remain unchanged.

## Scientific scope

This advances empirical initialization uncertainty without initializing the
engine. Normoglycemia does not establish overall metabolic health; prediabetes
is not all insulin resistance; diabetes of any type is not verified T2D.
Medication, assay error, missingness bias, pediatric coverage, oldest-age
top-coding, institutionalization and temporal transport remain unresolved.

Sampling covariance does not identify longitudinal progression/reversal,
current-state mortality or a dietary causal dose/lag. Active parameters,
scientific blockers and numerical scenario results are unchanged. Outputs
remain validation-only; #1/#27/#57/#58 requirements remain unresolved.

Authorship: Codex-assisted analysis for the Food is Health-affiliated project,
October 1, 2026 UTC. Scope-limited research-backed method assessment; external
expert review pending and no independent human scientific review claimed.
