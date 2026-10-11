# Selected blood-record coverage for the public meal-response study

This stage follows the [source/header preflight](HUTELIN_PUBLIC_FOOD_RESPONSE_INTAKE.md)
and advances I-07/I-11, F-08/T-08 and issues
[#58](https://github.com/Crusonia/Demeter/issues/58)/
[#117](https://github.com/Crusonia/Demeter/issues/117).
The [frozen contract](validation/hutelin2026-blood-coverage-protocol-v1.json)
defines one finite descriptive analysis of
[Hutelin's public CC0 data](https://doi.org/10.7294/32077803.v2).
Publication results and source headers were known before this design; it is
used-source development, not preregistration or independent prediction.

## Selection and interpretation

Only `data/raw/blood.csv` is decoded after the original-source/header guard.
Person, condition and time labels are private keys. Four prepared assay columns
receive availability classification: `glucose`, `insulin`, `insulin_w0` and
`insulin_impute`. A finite numeric value establishes availability in this source
column, not raw assay provenance or a clinical observation. Empty and literal
`NA` tokens are missing; other nonnumeric/nonfinite tokens remain unclassified.
Zero stays a numeric value. No concentration threshold or disease state is assigned.

The UTF-8 CSV reader transiently decodes complete row strings before projecting
the declared fields. The other six columns receive no statistical interpretation,
linkage, output or persistence. Malformed framing, embedded record newlines,
blank/short rows or size/row-limit breaches fail without a partial report. Source
bytes are never repaired or silently truncated.

Every accepted flat record is accounted for as a valid supported key or an invalid
key, with nonexclusive invalid reasons kept separate. Duplicate keys and their
extra rows remain visible; no record is silently deduplicated. Participant pairing
is counted from valid keys, independently of assay availability. Keys, dates,
measurements and person-linked results are never exported.

The report keeps two reference grids separate: the nine code suffixes and the
eight-label alternative suggested by the published post-meal schedule, using
an **unverified** source-0 baseline label. Grid coverage is not validation of
collection clocks, visits, assay lineage or an AUC horizon. Neither the method's
pre-meal baseline nor the plotting offset is inserted as an observed time.

## Reproduction

Use the six original files described in the preflight guide. After ordinary
[installation](GETTING_STARTED.md), this offline command works on all platforms:

```text
uv run python scripts/verify_hutelin_coverage.py --raw-dir data/raw/clinical/hutelin2026-documentation-20261011 --output outputs/hutelin-blood-coverage.json
```

The output must be new. Changed protocol, source and header identities fail before
participant decoding. The one selected blood member is read in memory and its
full decompression/CRC is verified. There is no ZIP extraction, network request,
author-code execution, imputation, demographic/date intake, AUC calculation or
clinical fitting. The output consists of source identities and aggregate
record/key/time/assay coverage. Technical bounds are not scientific parameters.

The protocol and synthetic implementation are committed before the first real
row inspection. Ordinary tests use constructed records and byte streams, including
private-marker checks and independently counted examples. CI must not open the
excluded source ZIP. A source-specific empirical receipt is a subsequent stage;
it cannot be inferred from synthetic tests.

## What this does not resolve

These counts cannot decide why a value is missing, establish the preparation of
the insulin variants, reconstruct source collection times, correct selection or
identify an acute meal effect. A paired response analysis still requires a frozen
estimand, baseline/integration rules, uncertainty, period/sequence and missing-data
sensitivity. A compatible food-to-clinical-state bridge and independent evaluation
remain required for #58. This stage admits no active parameter or scientific claim.
