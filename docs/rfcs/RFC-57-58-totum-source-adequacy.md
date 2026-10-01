# RFC-57/58: Verify the public TOTUM63 observation surface before fitting

- Status: source-row adequacy intake implemented; clinical likelihood not accepted
- Scope: [#57](https://github.com/Crusonia/Demeter/issues/57), [#58](https://github.com/Crusonia/Demeter/issues/58), #1 and milestone #27
- Selection: [frozen protocol](../validation/totum-source-row-protocol-v1.json), committed as `d059176` before numerical row inspection
- Assessment: source-specific software and methods appraisal, with separate Codex critique; external human scientific review pending
- Scientific use: source-layout diagnostics only; no efficacy estimate, rate fitting or engine activation

## The decision

Check whether a public release preserves observations that a future clinical model
could use. The current [clinical observation contract](../CLINICAL_OBSERVATION_CONTRACT.md)
requires more than adjacent baseline/follow-up columns. It needs a supported
record unit, measurement validity, observation timing and treatment/stopping
semantics. The selected release is a concrete way to examine those requirements
without manufacturing a clinical history.

This advances the health part of P-02 and inputs I-01, I-07 and I-11/I-12 in the
[design records](../design/README.md). L-00 remains accounting structure, not causal
evidence. The intake supplies no value-chain, agricultural, investment or
healthcare-cost conclusion and preserves the v0.1 health boundary.

## What the source permits

The [primary article](https://www.nature.com/articles/s41467-026-75626-0) describes
a supplement trial with a blinded TID comparison and an exploratory open-label
BID arm. Its [public Figshare v1 release](https://doi.org/10.6084/m9.figshare.32348169.v1)
has a verified CC BY 4.0 workbook. Table 4 explicitly labels baseline and
six-month fasting plasma glucose in mg/dL. The frozen selection includes A:D
only, across all source arm rows, and uses no effect direction to select columns.

The selected worksheet provides no documented participant key, actual collection
date, treatment-withdrawal date, death/contact history or missing-code dictionary.
Column placement supports a source-layout association. It does not independently
certify that each row is one unique person with a valid paired assay.

The [reporting summary](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-026-75626-0/MediaObjects/41467_2026_75626_MOESM2_ESM.pdf)
describes public source data for tables/figures and routes additional clinical data
to request. The article's broader availability statement is retained separately.
The [trial registry](https://clinicaltrials.gov/api/v2/studies/NCT04423302) says IPD
sharing “NO”; that conflicts with publication availability language but does not
invalidate the separately verified release license. Neither statement certifies
complete participant histories. No author contact or access request is made.

## Preservation and interpretation

Preserve source sheet/row/column and raw cell kinds locally. Formula, error,
date-formatted numeric, Boolean, absent, explicit blank, empty text, opaque text,
positive finite, zero, negative and nonfinite values remain distinguishable.
Cached formulas are not laboratory evidence. Numeric-looking strings are not
coerced. Group labels are not forward-filled, and merged anchors are not expanded.
No cross-sheet or cross-biomarker participant join is constructed.

Public output contains aggregate type/layout coverage only. A positive finite
number establishes numerical availability, not a valid fasting measurement.
Empty layout positions are not withdrawn participants. Raw missing markers do
not establish no disease, no treatment or no death. The workbook's six-month
label and the planned protocol visit remain separate from unknown actual dates.

The source describes a LOCF sensitivity analysis; this intake performs no
imputation and adopts no missing-at-random or independent-censoring assumption.
Treatment-triggered withdrawal remains a material unobserved stopping process.

## Tests and the next gate

The implementation verifies the frozen contract, receipt identities and all
five local source byte pins before interpreting selected cells. Tests cover
scope/header drift, raw-kind accounting, malformed cells, immutable local
observations, unknown-token disclosure, no-network execution and CLI preservation
of source files. Canonical engine results must remain unchanged apart from
registry provenance. Raw documents and the workbook remain fetch-only; only
permitted aggregate diagnostics and transforms are distributed.

An intake passing software checks does not make the source fit-ready. A later
analysis needs a separate frozen specification establishing record/pair units,
assay validity and missingness/stopping semantics. A conditional available-record
endpoint distribution would still differ from a full randomized causal effect.
Clinical latent states, annual progression/recovery hazards, consumed UPF dose,
lag, independent evaluation and national transport remain unresolved.

The full acceptance requirements of #57, #58, #1 and milestone #27 remain open.
