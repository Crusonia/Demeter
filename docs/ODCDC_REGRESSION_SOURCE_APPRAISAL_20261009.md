# ODCDC regression study: public observation and supplement appraisal

Assessment: October 9, 2026. Supports [#57](https://github.com/Crusonia/Demeter/issues/57)
and the [community data request](https://github.com/Crusonia/Demeter/issues/115).
Published results were visible before review: this is used-source documentation,
not preregistration, independent validation or parameter intake.

## Source and decision

[Davoodian et al.](https://link.springer.com/article/10.1007/s00125-025-06555-8)
studies subsequent diabetes after observed prediabetes regression in eight
cohorts, including U.S. studies. Online publication was October 2025; the journal
issue is January 2026. The article and its
[public supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs00125-025-06555-8/MediaObjects/125_2025_6555_MOESM1_ESM.pdf)
were acquired; selected tables and flow diagrams were rendered and inspected.
Original PDFs remain immutable in ignored storage. The
[documentary receipt](validation/odcdc-regression-source-review-20261009-v1.json)
pins their bytes, extracted pages, locators and source questions.

**Useful observation-design evidence; insufficient public material for a clinical
transition fit.** Group assignment uses first-follow-up glycemia. Diabetes
classification retains prior diagnosis and treatment, so a low later fasting
glucose does not erase diabetes history. Adjusted association models and a
Fine-Gray competing-death sensitivity do not supply a joint transition/death
likelihood. This paper is distinct from the
[19-cohort Lancet analysis](PUBLIC_CLINICAL_SOURCE_UPDATE_20261003.md);
consortium overlap does not establish independent validation.

## Consequences for model design

| Contract requirement | Exact source locator | Required resolution |
| --- | --- | --- |
| Entry and selection | Article Methods; ESM Fig. 2, PDF14 | Repeated-follow-up eligibility and excluded-person dispositions; analyzed people cannot stand for all baseline entrants. |
| Clinical history | Article Ascertainment, PDF3; ESM Fig. 1, PDF13 | Retain diagnosis and medication history; source normoglycemia is not general metabolic health or T2D remission. |
| Risk entry | ESM Figs. 1-2; ESM Table 6, PDF8 | Clarify the source's left-truncation designation, time origin and exact likelihood treatment. |
| Clocks | ESM Table 3, PDF5; ESM Fig. 1 | Cohort medians and visit counts do not identify person-specific intervals or a common annual panel. |
| Death | ESM Table 9, PDF11, including footnotes | Fine-Gray subhazard ratios are not state death hazards or generator entries; joint counts, event clocks and risk sets remain unavailable here. |
| Missingness | ESM Fig. 2, PDF14; ESM Fig. 3, PDF15 | Covariate-missing percentages do not describe missed visits, death, withdrawal or selection. |
| Access and dependence | Article Data availability; ESM Tables 7-10 | Governance approval is required for records; marginal intervals do not supply joint covariance or national transport. |

## Source questions to preserve

The receipt records documentary literals and arithmetic, not clinical parameters.
Do not repair decimals, invent missing people or choose convenient denominators.

- **ODCDC-R-01/R-02:** ESM Tables 2 and 4 each sum to 8,108. The flowchart
  identifies 8,191 after follow-up exclusions and 6,861 in the final analysis.
  Table membership and filtering remain unreconciled; totals alone do not
  establish who overlaps or explain the differences.
- **ODCDC-R-03:** ESM Table 9 displays `1.66` in the p-value column for negative
  versus positive family history. Preserve this out-of-domain literal; no
  corrected value is supplied here.
- **ODCDC-R-04:** Abstract and Methods give different first-follow-up IQR upper
  endpoints. Neither can replace actual visit schedules.
- **ODCDC-R-05:** Selected sex subtotals in ESM Table 3 do not equal displayed
  totals. Unknown categories, selection and transcription explanations remain
  unresolved.
- **ODCDC-R-06:** ESM Fig. 1 describes subsequent follow-ups schematically,
  while Table 3 reports differing cohort visit counts. A common schedule cannot
  be inferred.

## Useful next contribution

A steward can offer metadata or sufficient permitted aggregates: reconciled
cohort/risk-set definitions, linked observation schedules, diagnosis/treatment
definitions, detection/confirmation intervals, and death/contact/missed-visit
dispositions. Explain left-truncation implementation and table/flowchart
membership. Preserve overlap with other ODCDC and ARIC analyses when defining
evaluation data. Follow the
[public data requirements](PUBLIC_LONGITUDINAL_DATA_REQUIREMENTS.md);
do not post participant records.

The article explicitly withholds public participant data under cohort governance.
Its CC BY 4.0 article license does not release those records. No access request,
terms assent or investigator contact was initiated.

Design trace: I-01/I-05/I-07/I-11/I-12 -> F-04/F-08 -> T-05/T-08 in the
[design registers](design/README.md) and
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md).
No evidence parameter, sampling distribution, equation or scenario changes.
Clinical fitting, initialization, engine activation and scientific release remain
unadmitted; the [v0.1 evidence gaps](EVIDENCE_GAPS.md) remain open.
