# Public mortality evidence for issue #1

NHANES 2011–2012 baseline glycemic observations can be linked to subsequent
mortality without restricted ARIC records. Five original CDC/NCHS files are stored
in `data/sources/nhanes-mortality/2011-2012`, with exact-byte checksums, retrieval
times, official links and reuse notices. This advances the mortality evidence
route. It does not complete scientific validation or estimate clinical hazards.

## Source and observation contract

The [CDC linked-data page](https://www.cdc.gov/nchs/linked-data/mortality-files/index.html)
distinguishes public follow-up through 2019 from restricted follow-up through
2022. The latter is not available in this public store.
The [public-use description](https://www.cdc.gov/nchs/data/datalinkage/public-use-linked-mortality-file-description.pdf)
and [official reader](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/R_ReadInProgramAllSurveys.R)
define the linkage fields. `SEQN` joins only the same public survey cycle;
unmatched demographic/mortality IDs and duplicate IDs fail explicitly.

`ELIGSTAT=1` means linkage eligible. Codes 2 (minors excluded from public release)
and 3 (insufficient linkage information) have missing outcomes, not survival.
`MORTSTAT` is vital status. `PERMTH_EXM` gives examination follow-up; missing
and zero months remain visible. Some public follow-up times and causes of death
are perturbed; vital status is not. Published times are preserved without
inferring exact death dates or clipping them to an assumed calendar interval.

The registered joint A1c/fasting-glucose classification is applied to `DIQ_G`,
`GHB_G` and `GLU_G`. Cutoffs, adult age, pregnancy exclusion and age domains come
from the evidence registry. The death-certificate `DIABETES` flag is never a
baseline diagnosis. Survey normoglycemia, prediabetes and all-type diabetes do
not silently initialize the engine's broader healthy/IR/T2D states.

This cycle uses fasting weight `WTSAF2YR`, not the combined pre-pandemic weight
`WTSAFPRP`. All positive fasting-weight records remain in the variance design.
Linkage eligibility fractions use Taylor ratio variance, masked strata/PSUs and
logit-t intervals. Boundary estimates have no fabricated zero-width interval.
Original weights are not adjusted for linkage ineligibility; full NCHS reliability
screening and mortality-risk estimation are not implemented in this audit.

## Reconstructed development-sample coverage

There are 9,756 source respondents and 2,842 with positive fasting weights.
Of 2,294 adult, nonpregnant fasting participants, seven lack complete glycemic
observations. Of 2,287 complete baselines, 2,284 are linkage eligible and three
are ineligible.

| Baseline observation | Complete baselines | Linked records | Observed deaths |
| --- | ---: | ---: | ---: |
| Normoglycemia | 893 | 892 | 39 |
| Prediabetes | 960 | 959 | 93 |
| Diabetes, any type | 434 | 433 | 96 |

These are unweighted audit counts from pinned sources, not population prevalence,
annual risks, excess hazards or causal effects. The JSON also reports age/sex
cells and follow-up completeness. Overall and subgroup rows overlap; do not sum
them together. Public age is top-coded at 80, precluding single-age elderly
hazards. This inspected cycle is development data, not an untouched holdout.

## Before fitting

1. Specify the observation mapping to engine states, retaining diabetes type
   and glycemic-versus-metabolic distinctions.
2. Declare the mortality estimand, covariates and age structure. Baseline-state
   survival associations do not automatically identify hazards for changing
   current states; subsequent state changes and confounding require treatment.
3. Assess missingness, linkage weighting, sparse cells, design uncertainty and
   perturbed follow-up. Do not fit independent single-age/sex/state parameters
   to sparse cells.
4. Freeze a training/validation protocol and acceptance metrics before fitting.
   Additional disjoint cycles must be selected before model selection; this
   inspected cycle cannot later become an untouched holdout.
5. Validate mortality jointly with state prevalence and longitudinal health
   transitions. This linkage has no repeated glycemic observations and cannot
   identify progression, reversal, dietary response or intervention lag.

## Reload

```powershell
uv run demeter data rebuild-linked-mortality
uv run demeter evidence linked-mortality --output outputs/linked-mortality-audit.json
uv run demeter data verify-store
uv run demeter data verify-packages --check-tracked
```

Rebuilding is offline and byte-identical. Derived aggregates are packaged; raw
public-use files remain in the repository store. No row-level joined data or
restricted records are exported. [Data notices](../data/NOTICE.md) retain source
credit, public-use restrictions and non-endorsement. Issue #1 remains open for
the [full objective](CODEX_V0_1_OBJECTIVE.md); scientific mode remains disabled.

## Evidence-change record

Before this change there was no linked-mortality dataset. The new registry key
`nhanes_linked_mortality` has status `derived`, grade C and role
`feasibility_only`. Grade C reflects useful observational linkage with selection,
measurement and causal-identification limits; it is not an effect-size weight.
No engine parameter value, unit, grade, distribution or bound changes. No new
sampling distribution enters uncertainty or sensitivity analysis. Competing
interpretations of state mortality remain unresolved rather than being selected
by this audit.

The [before/after receipt](validation/issue-1-linked-mortality-before-after.json)
compares baseline and UPF-reduction scenarios with the prior registry on main.
Every output value is identical except the registry provenance hashes in model
and healthspan metadata. This is software equivalence, not scientific validation.
The source manifest records exact URLs, retrieval times and original hashes;
the packaged derived manifest records the transformation and definition hash.

Software verification on Windows: 384 tests passed, Ruff passed, source/package
verification passed, and the scientific-required command continued to exit 1.
Independent scientific review and clinical parameter acceptance are not claimed.
