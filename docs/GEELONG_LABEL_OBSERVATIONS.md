# What the Geelong follow-up labels tell us

Demeter now reproduces two complete rows of published follow-up glucose labels
from the male Geelong Osteoporosis Study. This adds actual observations of
movement in both directions between labels, with dependent category uncertainty.
It is one step toward learning progression and reversal over time. The table
does not yet identify clinical transition rates or a dietary effect.

Harland JW et al., *Risk Factors for the Progression or Regression to Diabetes
or Normoglycaemia for Men with Impaired Fasting Glucose*, Journal of Diabetes
Research (2025), article 9926306, [doi:10.1155/jdr/9926306](https://doi.org/10.1155/jdr/9926306).
The [primary XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12534155/fullTextXML)
contains the literal counts in section 3.4. Sections 2.2 and 3.4 independently
reconcile 446 sufficiently assessed pairs, 30 baseline diabetes exclusions and
416 participants in the progression analysis.

| Source baseline label | Follow-up normoglycaemia | Follow-up IFG-ADA | Follow-up source diabetes | Starting row total |
| --- | ---: | ---: | ---: | ---: |
| Normoglycaemia | 281 | 32 | 11 | 324 |
| Impaired fasting glucose, ADA definition | 44 | 27 | 21 | 92 |

Read each row as a partition of its published starting group. For example, 44
of the 92 assessed men starting with IFG-ADA had a normoglycaemia label at
follow-up. That is a conditional observation fraction, 44/92; it is not an
annual recovery rate or confirmed untreated remission. The overlapping WHO
categories are excluded rather than pooled with the ADA rows.

## Reproduce it from a fresh clone

After the [normal installation](../README.md#run-locally-or-in-codex-cloud), run these commands
from the repository directory on macOS, Linux or Windows PowerShell:

```text
uv run demeter evidence geelong-labels --output outputs/geelong-labels.json
uv run demeter evidence geelong-labels --descriptive-only --output outputs/geelong-descriptive.json
uv run python scripts/verify_geelong_labels.py
uv run demeter data verify-packages --check-tracked
```

The source XML, frozen selection, derived aggregate bundle and evidence registry
are included in the repository. Both modes run offline and import no participant
records. The first mode reports the working likelihood and its uncertainty.
The descriptive mode reports counts and fractions, with inferential outputs
explicitly unavailable. In PowerShell, `Get-Content outputs/geelong-labels.json`
shows the saved report; on macOS/Linux, use `cat outputs/geelong-labels.json`.

`--source PATH` can check an exact local copy of the pinned publication. A missing,
changed or inconsistent source produces a failure report and a nonzero exit
status. Input files and their aliases are protected from output overwrites.
A source revision requires a reviewed intake, not a silent upstream refresh.

## The working observation model

For each baseline row i, the three counts c_ij sum to its total n_i. The declared
conditional multinomial likelihood is

```text
L(P | C,n) = product_i [ n_i! / product_j(c_ij!) * product_j(p_ij ^ c_ij) ]
sum_j p_ij = 1
p_hat_ij = c_ij / n_i
Cov(p_hat_i) = [diag(p_hat_i) - p_hat_i p_hat_i^T] / n_i
```

There are two free probabilities per row. Increasing one category's fraction
constrains the others; six independent parameter draws would lose that
relationship. The report retains a six-coordinate covariance matrix with
negative within-row covariances and singular row blocks.

This working model assumes independent observations within each starting row,
a common marginal probability for the source's actual timing/age/selection
mixture, and conditional independence of the two disjoint starting groups given
their totals. The source does not establish these assumptions. The fitted
probabilities describe the selected observations under those assumptions.

Each cell is also treated as that category versus all other categories for an
exact binomial Clopper-Pearson interval. Bonferroni allocation across all six
cells provides at least 95% simultaneous coverage under the working sampling
model. These rectangular intervals need not jointly lie on the simplex and
are not an independent sampling distribution. They do not quantify selection,
measurement, diagnosis history, treatment, timing, transport or structural
uncertainty. Derived registry numbers use the repository's 12-significant-digit
storage convention; that is not a claim of empirical precision.

## Why this is not yet a clinical transition fit

The target is the unweighted follow-up label distribution conditional on a
source baseline ADA label and selection into the paired, sufficiently assessed
male subset in south-eastern Australia. It averages the source's actual entry
and follow-up timing mixture. It does not describe everyone recruited or the
U.S. population.

- Entry could be at the original 2001–2006 or later 2007–2010 assessment. The
  follow-up phase was finalized in 2022. Individual clocks and event times are
  absent; dividing by a nominal 15 years or median duration is unsupported.
- Source diabetes uses fasting plasma glucose, self-report or antihyperglycemic
  medication. It is not independently confirmed incident type 2 diabetes;
  baseline diabetes includes type 1. Source labels do not enforce persistent
  diagnosis history. One follow-up blood test lacks repeat confirmation.
- The medication statement attached to IFG regression analysis does not establish
  medication-free status throughout follow-up. A lower glucose label is not
  evidence of untreated clinical recovery or diagnosed remission.
- Deaths, losses and insufficient assessments are outside these paired rows.
  No complete baseline-label-specific death/unassessed partition is available.
  Unobserved outcomes remain unknown rather than being completed with zeros.
- There is no selected dietary dose, causal contrast or lag. No annual
  generator, mortality schedule, national initialization or health-cost result
  is fitted or activated.

All 17 registered quantities are `benchmark_only`: exact reported integers are
`observed`; ratios and conditional working intervals are `derived`, evidence
grade C. Active clinical parameters and canonical simulation results remain
unchanged and validation-only. The full requirements of issues
[#57](https://github.com/Crusonia/Demeter/issues/57),
[#58](https://github.com/Crusonia/Demeter/issues/58),
[#1](https://github.com/Crusonia/Demeter/issues/1) and
[#27](https://github.com/Crusonia/Demeter/issues/27) remain open.

## Reproducibility, rights and the next evidence gate

The [frozen protocol](validation/geelong-label-protocol-v1.json) records selection,
equations, assumptions, failure rules and retained requirements. Source discovery
and two reviewers had already exposed the selected cells and nearby results
before the freeze. The protocol was committed before numeric intake; this is
used-source selection, not preregistration, blinding or an untouched holdout.
The [intake receipt](validation/geelong-label-intake-receipt-v1.json) records the
chronology. Existing discovery receipts remain unchanged.

The [unmodified XML](../data/sources/geelong/2026-10-01/publication.xml) retains its
copyright and Creative Commons Attribution notice, whose version is unspecified.
Attribution, receipt hashes and the [rights inventory](../data/rights.json) travel
with it. Publication reuse does not grant participant-data access; no participant
records were requested, acquired or exported. Demeter does not relicense source
content. The [bundle](../src/demeter/data/bundled/geelong_label_pairs.json) contains
only selected aggregate counts and provenance.

The [reproduction report](validation/issue-57-geelong-labels.json) and
[before/after proof](validation/geelong-labels-before-after.json) distinguish
used-source reproduction, independent mathematical software checks and engine
regression evidence from independent clinical validation. Compatible linked
clocks, ascertainment/history/treatment/stopping, observation-to-state mapping,
identifiable progression/reversal and mortality, joint clinical uncertainty,
independent trajectory evaluation and national transport remain required.
Dietary causal identification is a separate unresolved requirement.

The design trace is Q-03/RM-04 → P-02 → I-01/I-07/I-11/I-12 → F-08 →
T-01/T-02/T-05/T-06/T-08 in the [model design records](design/README.md).
This is an observation foundation within the health phase. It preserves the
long-term value-chain vision without activating later food, payer or economic
mechanisms before the health acceptance criteria are met.
