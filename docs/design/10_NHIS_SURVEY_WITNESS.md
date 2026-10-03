# Synthetic NHIS joint-ratio software witness

Status: implemented software mechanics tested with synthetic inputs only. No NHIS
participant file, national estimate or clinical initializer is admitted here.
The existing [reported-diagnosis design](09_NHIS_REPORTED_DIAGNOSES.md) remains the
source-facing proposal. Before using reported type 2 diagnoses in a baseline,
we need to show that the calculation preserves unknown answers and accounts for
the dependence between categories and overlapping survey groups.

The design chain is I-01/I-07/I-11/I-12 -> F-08 -> T-05/T-08 in the
[input register](04_MODEL_INPUTS.md) and
[formulation register](05_FORMULATION_AND_TESTS.md), alongside
[RFC-56](../rfcs/RFC-56-observation-state-mapping.md). This advances the numerical
observation interface within the [v0.1 objective](../CODEX_V0_1_OBJECTIVE.md);
it adds no dietary effect, clinical transition or mortality parameter.

## Implemented contract

The [pure adapter](../../src/demeter/data/nhis_survey_witness.py) accepts a
synthetic in-memory DataFrame with native-named `DIBEV_A`, `DIBTYPE_A`, `WTFA_A`,
`PSTRAT` and `PPSU` columns, plus aligned caller-supplied Boolean domain columns.
It uses the unchanged [categorical witness](../../src/demeter/data/nhis_diagnosis_labels.py)
to assign every record to exactly one of seven categories, including unknown
diagnosis, diagnosed-but-unknown type and inconsistent type-universe answers.
Record counts are not counts of an admitted population or unique people.

For domain D and recorded category C the ratio is
`sum(w * I(D) * I(C)) / sum(w * I(D))`. Categories remain a complete partition;
unknown and inconsistent answers never disappear from the denominator. Caller
domains may overlap. Coordinates are domain-major, then the classifier's fixed
category order. Ratios are dimensionless and their covariance has squared
dimensionless units. Empty domains return unavailable ratios and covariance
coordinates, rather than zero. An empty input frame is refused by this method.

Only a copied design projection is privately aliased into the existing unchanged
[joint Taylor kernel](../../src/demeter/data/survey_joint.py). The adapter reuses
its compensated reductions and complete first-stage with-replacement covariance.
Every supplied design row remains, including rows outside all requested domains.
No independent-category approximation, covariance repair or source parsing is
introduced. The adapter builds new native-labelled metadata; the kernel's NHANES
labels and descriptive PSU-minus-strata fields are not emitted as NHIS inference.

The supported software method requires finite positive weights and at least two
PSUs in every full-design stratum. Zero, missing or otherwise unsupported weights
and full-design singleton strata cause a sanitized refusal; records are never
silently trimmed. These are current software-method limits, not official NHIS
eligibility rules or evidence that a clinical quantity is unidentified. Numeric
design labels are only synthetic grouping keys here; this is not a native code
decoder. The adapter does not establish an interval, inferential degrees of
freedom, finite-population correction policy or NCHS presentation reliability.

## Evidence and admission boundary

The source field meanings remain documented in the earlier design and its
[metadata receipt](../validation/nhis2025-typed-diagnosis-design-receipts-v1.json).
The official [2025 NHIS catalog](https://www.cdc.gov/nchs/nhis/documentation/2025-nhis.html)
and [Sample Adult codebook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2025/adult-codebook.pdf)
are documentary sources, not empirical inputs to this witness. Their inspection
preceded this work: this is used-source software development, not preregistration
or independent validation of publication results. No new source values or
scientific parameters are added to the evidence registry.

The result is a private synthetic aggregate record ledger with ratios/covariance.
There is no file loader, CLI, participant export, source admission or engine
connection. An in-memory function cannot establish whether its caller's records
are synthetic; callers must not promote its label to a source audit. All five
gates remain literally false: `direct_initialization_allowed`,
`clinical_fit_allowed`, `engine_activation_allowed`,
`sampling_distribution_assumed` and `scientific_release_ready`.

A future empirical build must separately freeze native file/format identities,
adult target and proxy/age/sex unknown partitions, full eligible annual design,
source weight and singleton handling, interval/df and presentation policies,
privacy rules and loaded-code admission before calculation. The present positive
weight refusal cannot settle those choices. Reported diagnosed type 2 remains a
recorded-answer estimand; it does not identify undiagnosed or total T2D, current
clinical activity, remission or age-specific transition hazards. It cannot be
subtracted from NHANES to manufacture a common metabolic-state partition.

## Software falsification

The [synthetic tests](../../tests/test_nhis_survey_witness.py) compare all ratios
and cross-domain covariance entries with an independent exact-Fraction oracle
using unordered PSU-pair differences, rather than the kernel's centering formula.
They check full category conservation, partition covariance closure, overlapping
and empty domains, retained out-of-domain PSUs, weight-scale and row-order
invariance, nonmutation, unknown/inconsistent responses, sanitized malformed-input
refusal and absence of inherited inferential metadata. These checks establish
software arithmetic only, not empirical transport, clinical identification or a
released NHIS benchmark.
