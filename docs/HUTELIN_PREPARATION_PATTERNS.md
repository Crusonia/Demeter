# Prepared insulin columns: finite source-pattern diagnostic

This stage follows [the actual blood coverage](HUTELIN_BLOOD_COVERAGE.md) for
[Hutelin et al.](https://doi.org/10.1038/s42255-026-01619-4).
It feeds I-07/I-11 and F-08/T-08. It introduces source-method quantities and a
finite preparation-pattern diagnostic, with no clinical state, annual hazard,
imputation replay, AUC or food effect. The clinical bridge required by
[#58](https://github.com/Crusonia/Demeter/issues/58) remains unresolved.

The [publisher supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs42255-026-01619-4/MediaObjects/42255_2026_1619_MOESM1_ESM.pdf),
page 9, reports an insulin quantification limit of 3 microIU/mL and replacement
of lower values using 3/sqrt(2), followed by covariate-informed imputation before
trapezoidal incremental AUC. It also specifies a successful-collection criterion
and keeps a participant with one unavailable condition in the analysis.
These are method declarations, not evidence that every prepared numeric cell
is an observed concentration. They do not explicitly map the delivered three
insulin column names to preparation stages.

The article's notice is **CC BY-NC-ND 4.0**, with third-party exceptions; its
full PDF/HTML stay ignored/fetch-only. The independently posted producer dataset
is marked **CC0**, a separate artifact. Only limited attributed method facts,
source identities and our authored diagnostic travel here. No source expression,
figures, adapted publication or participant records are distributed.

## Declared diagnostic

The [frozen protocol](validation/hutelin2026-preparation-pattern-protocol-v1.json)
selects only the three insulin columns after verifying source/documentary
identities and bounded flat CSV framing. Other row strings are transiently
decoded before projection, with no interpretation, persistence or output.
Every record receives one exclusive status; duplicate records remain counted.

The status names preserve the column called `insulin` as the native-labelled
column, without asserting that it is an unmodified assay. They distinguish all
missing, unclassified tokens, missing native values with other prepared patterns,
equal prepared values, missing prepared values and discrepancies. A special
pattern asks whether a missing native-labelled value has a zero in `insulin_w0`
and a compatible replacement in `insulin_impute`. Matching that pattern does
not prove a censor flag, explain missing collection or qualify a clinical value.

Compatibility uses a proposed nearest-last-printed-decimal interval around the
stored token. Its half-width is half the printed decimal quantum, with both
boundaries included. The target is the registered binary64 evaluation of the
published formula. This is a **storage hypothesis**, not a verified rounding
rule, biological interval or tolerance selected to get a desired match count.
The protocol fixes Decimal precision and numeric size/exponent bounds before
additional real-value interpretation. Unsupported tokens remain unclassified.

The quantification limit and replacement are benchmark-only observed/derived
method records in `evidence/parameters.yaml`. The interval convention is an
explicit benchmark-only modelling definition. Fixed uncertainty describes these
definitions, not zero assay, imputation or effect uncertainty. None is an engine
input or a clinical sampling distribution.

## Replay after obtaining the original files

Use the original six preflight files plus the matching publisher supplement,
saved as `publisher-supplement-original-20261011.pdf` in the same ignored folder.
Do not repair source bytes or change a hash to make a new delivery pass.

```text
uv run python scripts/verify_hutelin_preparation.py --raw-dir data/raw/clinical/hutelin2026-documentation-20261011 --output outputs/hutelin-preparation.json
```

The output must be new. The command is offline, executes no R code and exports
only pattern counts and source/protocol/runtime identities. Source methods,
registry role/definitions, original documents, ZIP/header/member identities and
framing are checked before extra value interpretation. The source file is read
in memory; no identifiers, dates or concentrations appear in the report.

The contract and synthetic implementation precede the first such invocation in
[6a70af3](https://github.com/Crusonia/Demeter/commit/6a70af3).
Publication, code, source headers and aggregate coverage were already known:
this is used-source development, not preregistration or independent validation.
Ordinary tests use constructed rows and guards. They do not open excluded raw
records or establish actual assay provenance.

The [actual original-source result](validation/hutelin2026-preparation-pattern-result-v1.json)
accounts for all 466 records: 421 have equal finite values across all three
columns, 38 have a missing native-labelled cell with the zero-and-replacement
compatibility pattern, and seven have all three cells missing. No unclassified
token or other discrepancy pattern occurred under this frozen diagnostic.
The result pins the executing module, source member, registry and protocol.
It exports no individual value or identifier.

This explains the previously reported availability difference without treating
prepared cells as measurements. It does not verify the hypothesized rounding
policy, the cause of each missing cell, or a source censor flag. Counts do not
select participants for a clinical analysis or qualify concentrations.

## Remaining interpretation requirements

The declared package version 1.13 manual preserves nonmissing continuous input
values in its output. It does not establish a unit-rescaling bug merely because
the author uses `tab.disj`. Actual covariate types, installed versions and the
full transformation lineage still need verification before replay. Source code
creates original/imputed indicators internally but drops them from final output.

A matching source pattern must remain distinct from verified assay/censor flags.
The source collection criterion cannot be reconstructed just by counting native
numeric cells: a successfully collected but censored sample can lack such a
value. Neither diagnostic status nor prepared values supply clinical eligibility,
annual transitions, national transport or the required dietary disease bridge.
