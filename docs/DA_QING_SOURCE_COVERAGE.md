# Da Qing: observed diagnosis history, mortality and dietary assignment

This new public-source intake advances the observation review for
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58). It reproduces literal
published death counts and person-time, checks their arithmetic, and preserves
a source inconsistency. It does not fit a hazard or activate a clinical parameter.

For a newcomer, a baseline glucose category and a person's later history answer
different questions. Someone initially assessed with impaired glucose tolerance
can later be diagnosed with diabetes. This source assigns their later person-time
to a different diagnosis-history category. It is therefore a useful complement
to the repository's mortality predictors based only on baseline observations.
It cannot by itself tell us that preventing diabetes would cause the same change
in mortality, or that someone without a diagnosis remained in a particular
glycemic state.

## What is reproduced

[Gong et al. (2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5001147/),
DOI 10.2337/dc16-0429, follows the original Da Qing impaired-glucose-tolerance
trial cohort in China. Its Table 2 reports death-count/person-year pairs for
three updated-age groups and four time bands, both before and after recorded
diabetes diagnosis. The same person may contribute exposure to multiple cells;
these are not independent participant cohorts.

The [recorded audit plan](validation/da-qing-source-audit-protocol-v1.json)
selects 24 age-by-time cells, their published all-age and total rows, and limited
Table 1/narrative denominator crosschecks. Published outcomes were already
inspected when the plan was recorded; this is used-source reproduction, not
preregistration or independent evaluation. The
[machine-readable coverage](validation/da-qing-source-coverage-v1.json)
preserves each literal pair, its exact table locator, source receipt, display
precision and audit disposition.

The selected death/exposure row and column totals agree. Table 1's cohort and
death partitions also agree with the selected narrative denominators. However,
the narrative reports 428 incident diabetes diagnoses while the first two
diagnosis-time groups in Table 1 already total 437. This discrepancy is
unreconciled. No source value is corrected, substituted or converted to an
annual probability. A successfully reproduced audit retains
`source_consistency_passed: false`.

## Observation and inference limits

| Source observation | Supported interpretation | Requirement still unresolved |
| --- | --- | --- |
| Deaths and whole person-years in updated age/time cells | Published descriptive exposure and event-count partitions | Individual clocks, displayed exposure rounding, clinic dependence and joint uncertainty |
| Recorded diabetes diagnosis, including medical history or glucose-lowering treatment | A diagnosis-history category distinct from an initial glucose result | Biological onset, current glycemia, diagnosis delays and compatible engine-state mapping |
| Time before recorded diagnosis | Follow-up exposure in people initially assessed with impaired glucose tolerance | Unmeasured regression to normal glycemia; it is not verified continuously persistent prediabetes |
| Repeated OGTT assessments during the original trial and later clinical follow-up | An explicit observation schedule with changing ascertainment | Systematic intermediate glucose assessments after the original trial; source-reported limitations remain |
| Death certificates, proxy reports, records, last contact and incomplete follow-up | Death and loss were considered in the source analysis | Complete released joint clinical paths and a justified selection/missingness likelihood |
| Time-dependent adjusted mortality association | Diabetes history was updated in the source statistical model | A causal effect of changing clinical state, changing confounders, U.S. transport and independent predictive evaluation |

No Poisson or binomial sampling distribution, independent confidence intervals,
clinical mortality ratio or dietary coefficient is introduced. This intake
contains public publication-level aggregates only, with no participant records.
The raw HTML has an ADA educational/nonprofit/unaltered-use notice; public
access does not establish unrestricted redistribution. The source stays in
ignored, fetch-only storage. The repository contains attributed aggregate facts,
authored audit code and receipts.

## The separate diet-only route

[Pan et al. (1997)](https://doi.org/10.2337/diacare.20.4.537) originally assigned
clinics to diet-only, exercise-only, combined intervention or control.
A categorical diet-only regimen is a potentially compatible food intervention
to appraise; it need not be recast as a continuous UPF dose. The ordinary
publisher PDF request returned HTTP 403, so this intake does not extract its
outcome cells, missingness dispositions or cluster uncertainty.

The later [Gong et al. (2019) follow-up](https://pmc.ncbi.nlm.nih.gov/articles/PMC8172050/)
is separately identified and its primary HTML is acquired in the receipts. That
report pools intervention groups. It must not substitute for the original
diet-only contrast, and the overlapping publications must not be treated as
independent cohorts. This intake performs no numerical reproduction of the
later report.

Advertised PDF links for the 2016 main paper and supplement returned HTTP 200
with HTML rather than PDF bytes. They were not accepted as source PDFs. The CDC
manuscript requests returned HTTP 403. Successful HTML pins and failed document
requests are separate in the receipt artifact; no challenge interaction,
credentials, agreement, data application or investigator contact occurred.

## Run the checks

```bash
uv run python scripts/verify_da_qing_source_coverage.py
```

The current command exits 1 because the source consistency check fails, while
also reporting whether the registered authored artifact reproduces correctly.
This is an intentional scientific disposition, not a parser failure. An
optional local exact-byte replay verifies extraction against the acquired HTML:

```bash
uv run python scripts/verify_da_qing_source_coverage.py --article-cache outputs/da-qing-source-sprint-v1/gong2016-pmc-article.html
```

The cache is optional and does not ship with a clone or package. A newly retrieved
HTML representation may differ in bytes; it cannot silently replace this pin.
The tests exercise source identity, checksum, table labels, units, invalid
counts, conservation, failed checks and the clinical boundary using explicit
synthetic parser fixtures and the committed public aggregate observations.

This feeds I-01/I-07/I-11/I-12 and F-04/F-08, with T-05/T-08 observation and
validation requirements in the [design registers](design/README.md).
The clinical observation contract, historical end-to-end dietary validation and
scientific v0.1 acceptance criteria remain open. Simulations remain validation-only.
