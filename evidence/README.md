# Evidence registry

The [ARIC outcome benchmark](../docs/ARIC_OUTCOMES_BENCHMARK.md) registers 44
observed publication literals and 14 derived static counts under `aric_panel_*`.
Its two public source receipts and conditional source reconstruction are
benchmark-only. Complete provenance is checksum-bound; no clinical likelihood,
sampling distribution, national transport or engine parameter is activated.

Demeter treats evidence as part of the model, not as prose surrounding the model.

The [Malawi follow-up benchmark](../docs/MALAWI_FOLLOWUP_BENCHMARK.md) registers
22 literal publication values and one derived untraced residual. Its source
threshold change, person-year discrepancy, confirmed deaths and missing people
remain explicit. Coupled completion bounds are finite-cohort information ranges,
not sampling intervals or annual hazards. No clinical input is activated.

The [joint glycemic uncertainty report](../docs/JOINT_GLYCEMIC_UNCERTAINTY.md)
estimates full survey covariance of existing observed-category partitions and
partial-membership endpoints. Shared respondents, unknowns and cross-domain
dependence are retained. It supplies no sampling distribution, latent-state
allocation or active initializer.

The [CDC prediabetes benchmark](../docs/CDC_PREDIABETES_BENCHMARK.md) retains its
observed point value and now records the published 95% interval from an archived
official PDF. Its offline check distinguishes crude prevalence from awareness
and age-adjusted estimates. It is not a sampling distribution or clinical input.

The [PREVIEW endpoint benchmark](../docs/PREVIEW_ENDPOINT_AUDIT.md) registers
literal cohort/count/definition values and published adjusted risk ratios under
`preview_endpoint_benchmark`. All are `benchmark_only`. Fixed uncertainty on
literal counts records the published value; it supplies no population sampling
distribution. Reported adjusted intervals and deterministic missing-label
envelopes remain separate. No clinical hazard, dietary dose, lag or national
parameter is activated.

[TOTUM63 source adequacy](../docs/TOTUM_SOURCE_ADEQUACY.md) adds five pinned sources
and a `benchmark_only` intake definition, with no new model parameter. Source-cell
coverage counts are fixed-release diagnostics, not clinical outcomes or people.
The frozen selection precedes numerical intake; the methods and headers were
already inspected, and no independent clinical validation is claimed.

[Whitehall II endpoint analysis](../docs/WHITEHALL_ENDPOINT.md) registers two
observed FPG-label counts and their derived denominator/proportion as
`benchmark_only`, plus two static source receipts. Its Clopper–Pearson interval is
an analyst calculation under explicit iid binomial working assumptions, not a
published interval. Confidence 0.95 is a declared analysis design setting in the
dataset metadata. Descriptive-only mode supplies no sampling interval. No
clinical transition, causal dietary effect or national parameter is activated.

[Paired remission observations](../docs/PAIRED_REMISSION_OBSERVATIONS.md) register
five literal source facts and three fetch-only DiRECT/NLM snapshots. They derive
coupled integer feasible tables, retaining a conditional common-ITT interpretation,
subgroup scope and unknown nonremission/assessment/death allocations. The accepted
fraction's conflicting denominator and failed intakes remain preserved. These
bounds are source-information ranges, not sampling intervals or annual rates;
no clinical input is activated.

Every substantive numeric parameter must be represented in `parameters.yaml` (or a future normalized successor) with units, status, provenance, evidence strength, and uncertainty where applicable.

## Status

- `observed`: read directly from a named source
- `estimated`: statistically estimated from source data or literature
- `derived`: computed deterministically from other registered values
- `synthetic`: software-validation placeholder only

Any simulation that materially depends on a `synthetic` parameter is **validation-only**.

The `toy_*` parameters belong only to the isolated
[stock/flow teaching example](../docs/LEARNING_PATH.md). They have synthetic
status, grade E and `benchmark_only` role to prevent health-engine use. Their
abstract tokens/ticks and illustrative distributions are not clinical inputs.

## Evidence grades

- **A**: strong causal evidence
- **B**: strong prospective/high-quality observational evidence
- **C**: useful observational or mechanistic evidence with meaningful causal uncertainty
- **D**: expert/modeling assumption
- **E**: synthetic development placeholder

Grades do not replace study-level appraisal and must not be converted mechanically into effect-size weights.

## Rule

Never invent a value or citation to make the model run. An unresolved parameter is a valid state; a fabricated parameter is not.

`observation_partial_mapping` registers a separate partial-observation alternative
to the complete-case state audit. It reports compatible-category bounds and
separate sampling intervals without imputation or engine activation. See
[partial observations](../docs/PARTIAL_OBSERVATIONS.md).

## Clinical candidate appraisals

The `food_exposure_ontology` dataset supplies the typed food/nutrient contract,
units, definitional bounds, overlap links and activation roles. `dietary_baselines`
registers historical NHANES/USDA transformation choices and NCHS UPF table locators.
Their immutable source receipts and derived JSON preserve observational status,
population, vintage and uncertainty. They do not identify causal coefficients.
See [food exposure definitions](../docs/FOOD_EXPOSURES.md) and run
`demeter food-exposures` or `demeter evidence dietary` to inspect them.

`sources` contains source URLs, DOIs, raw-byte SHA-256 receipts, retrieval times,
licenses, and correction notes. Appraised parameters carry `source_id`, an explicit
table locator and unit scale, the reported confidence interval, the intended model
input, and unresolved mapping problems. They must have `model_role: benchmark_only`.
The engine rejects benchmark records used in a required input slot, even when their
key and unit have been renamed. A published interval does not become a sampling
distribution automatically.

```bash
uv run demeter evidence applicability --output outputs/applicability.json
uv run demeter evidence verify-sources --download
```

The second command fetches missing source HTML into ignored `data/raw/clinical/`,
checks pinned hashes, and repeats the table extraction. It never updates the
registry or overwrites an existing raw file. HTML drift, unavailable sources,
missing artifacts, or changed extracted values fail explicitly. Without `--download`
it is entirely offline. Fresh downloads may fail a byte-level pin if the publisher
changes page markup; a reviewed source-receipt update is then required. The original
raw retrieval and six extraction results are recorded in
`docs/validation/issue-1-clinical-sources.json`. Only small factual estimates and
receipts are committed; full articles are not redistributed.

The [food-intake reproduction](../docs/FOOD_INTAKE_REPRODUCTION.md) adds a pinned
author archive and an estimated, benchmark-only paired menu contrast. Its own
`demeter evidence food-intake --archive PATH` command verifies and analyzes the
daily table; `verify-sources` checks archive bytes and repeats its registered
analysis through the dataset-specific verifier. Analysis
constants and the interval are registered, and the raw ZIP is excluded from all
distributions. This intake endpoint does not identify a diabetes or mortality effect.

`chen_followup_timing_audit` adds separate, benchmark-only duration and publication
arithmetic diagnostics under frozen protocol and amendment hashes. Run
`demeter evidence public-cohort-timing --workbook PATH --output PATH` against the
pinned Chen archive. It retains failing source checks and exits 1 after saving
the report; fitting and engine activation remain disabled. It does not change
the original intake protocol or receipt. See the
[timing audit](../docs/CHEN_TIMING_AUDIT.md).

The [Reus pathway assessment](../docs/REUS_DIABETES_PATHWAY.md) registers six
estimated, grade-C, benchmark-only Cox HRs and their reported intervals from the
separate corrected trial. Grade C describes this scoped use: corrected assignment,
post-randomization adjustment and unresolved engine/population applicability.
It is not a downgrade of randomized evidence in general. Shared arms and repeated
analyses have unknown joint covariance; no independent sampling distribution is
invented. The synthetic/E compatibility dataset pins seven existing reference
definitions and both invoked engine helpers before executing software witnesses.
Neither dataset activates a clinical effect. Use `demeter evidence reus-diabetes`
with local source XML, or `demeter evidence pathway-compatibility` offline.

`dpp_observation_contract` registers documentation definitions and their four
source pins; `dpp_observation_software_witness` registers an arbitrary synthetic/E
fixture. The dedicated `demeter evidence dpp-observations` command checks the
frozen contract and exports only aggregate software diagnostics. Optional `--raw`
verifies matching public documentation bytes. It does not re-extract clinical
tables, import participant records or establish their permitted use. Source-year
conversion, event/confirmation dating, clinical likelihood and engine activation
remain unresolved. See the [DPP guide](../docs/DPP_OBSERVATION_ADAPTER.md).

The [coverage appraisal](../docs/DPP_SOURCE_COVERAGE.md) and its separate receipts
record additional public form/dictionary meanings, excluded dates and version
discrepancies. They are design/provenance artifacts, not new parameter evidence
or an extension of the frozen four-source synthetic contract.
