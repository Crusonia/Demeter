# UPDATE published biomarker source-summary replay

This offline benchmark reproduces limited published summary facts, not Demeter
predictions or independent clinical validation. It feeds I-11/F-08/T-08 and the
[RFC-58 dietary contrast](rfcs/RFC-58-food-pathway-identification.md).
The exposure and disease-transition bridge remains unresolved.

```powershell
uv run python scripts/verify_update_biomarker.py
uv run python scripts/verify_update_biomarker.py --output outputs/update-biomarker-report.json
```

The output path must be new. The first command checks the committed source
summary and complete scoped evidence metadata; it does not read the original PDF.
With a previously obtained matching public PDF, the optional replay is:

```powershell
uv run python scripts/verify_update_biomarker.py --source-pdf data/raw/update/update-current-publisher-supplement-original.pdf
```

There is no network call. Different PDF bytes are rejected before extraction.
The original replay emits pypdf's generic nonzero-indexed xref-table warning;
the decoder handles that internally. No source bytes are rewritten or repaired,
and the source checksum remains the selected original's checksum.
The complete PDF, full text and figures stay ignored/fetch-only by project choice.
The [article's CC BY 4.0 notice](https://www.nature.com/articles/s41591-025-03842-0)
includes a third-party credit exception. The snapshot attributes limited numeric
facts and identifies renamed units/groups; see [the license](https://creativecommons.org/licenses/by/4.0/).

## Exact implemented scope

[Dicken et al., Nature Medicine (2025), DOI 10.1038/s41591-025-03842-0](https://www.nature.com/articles/s41591-025-03842-0)
compared supplied ad-libitum diets following UK guidance in a community crossover
trial in England. Diagnosed T2D was excluded. The
[current public supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41591-025-03842-0/MediaObjects/41591_2025_3842_MOESM1_ESM.pdf)
Table 5, PDF page 12, supplies only these selected rows:

| Source endpoint | Change unit | Selected groups and columns |
| --- | --- | --- |
| HbA1C (%) | percentage points | MPF, UPF, paired MPF-minus-UPF: N, mean, reported SE |
| Fasting glucose (mmol/L) | mmol/L | MPF, UPF, paired MPF-minus-UPF: N, mean, reported SE |

The window is each diet's baseline to week eight. Page 13 identifies paired
t-tests. Preserve the source's ITT table label alongside endpoint-specific
available-case and paired counts; these are not all randomized participants.
The paired glucose contrast is retained literally rather than calculated from
the separately reported marginal means. All selected quantities, including the
assessment window, are `benchmark_only` evidence records. Selection followed
inspection and an independent visual row check; this is used-source reproduction.

Printed SEs have one decimal; HbA1c's displayed `0.0` is not zero biological or
sampling uncertainty. The report preserves numeric and display forms, while
underlying uncertainty, covariance, sampling distribution and confidence intervals
remain null. Mean/SE registry records intentionally have null uncertainty, so the
evidence audit exposes incompleteness. No p-value, inferred rounding rule or
confidence interval is selected or recalculated. Source biomarkers were collected
after an overnight fast; nonfasted week-four visits do not establish a fasted
glycemic trajectory. [Methods](https://www.nature.com/articles/s41591-025-03842-0).

## Preserved scientific limits

Table 6 sequence/period and first-period parallel comparisons remain documented,
separate and numerically unimplemented. Carryover and selection remain unresolved;
per-protocol and other table analyses overlap the same trial. Secondary outcomes
are exploratory without multiplicity adjustment. The publisher's 2025-12-15
correction concerns Table 24 menu energy density; the current corrected supplement
is pinned without selecting those values. Offered menus differ from consumed
exposure. The data statement permits author-approved summaries, not individual
records; existing public aggregate tables are a separate source.
[Article and change history](https://www.nature.com/articles/s41591-025-03842-0).

The January 2026 publisher previews identify concerns about
[attribution to processing](https://www.nature.com/articles/s41591-025-04085-9),
[long-term interpretation](https://www.nature.com/articles/s41591-025-04087-7), and
[attrition/order and bundled diet differences](https://www.nature.com/articles/s41591-025-04088-6).
Full critiques and the [substantive reply](https://www.nature.com/articles/s41591-025-04089-5)
were inaccessible in the bounded review; no resolution is claimed.

This source replay does not refit a model, adjust attrition, annualize changes,
map biomarker means to disease states, estimate a consumed-UPF coefficient,
transport results to the U.S., or initialize the clinical engine. All five
scientific gates remain false. Existing model parity checks concern unchanged
software behavior and do not promote these summaries to model validation.
