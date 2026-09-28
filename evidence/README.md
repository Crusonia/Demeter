# Evidence registry

Demeter treats evidence as part of the model, not as prose surrounding the model.

Every substantive numeric parameter must be represented in `parameters.yaml` (or a future normalized successor) with units, status, provenance, evidence strength, and uncertainty where applicable.

## Status

- `observed`: read directly from a named source
- `estimated`: statistically estimated from source data or literature
- `derived`: computed deterministically from other registered values
- `synthetic`: software-validation placeholder only

Any simulation that materially depends on a `synthetic` parameter is **validation-only**.

## Evidence grades

- **A**: strong causal evidence
- **B**: strong prospective/high-quality observational evidence
- **C**: useful observational or mechanistic evidence with meaningful causal uncertainty
- **D**: expert/modeling assumption
- **E**: synthetic development placeholder

Grades do not replace study-level appraisal and must not be converted mechanically into effect-size weights.

## Rule

Never invent a value or citation to make the model run. An unresolved parameter is a valid state; a fabricated parameter is not.

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
