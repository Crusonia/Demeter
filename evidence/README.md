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
