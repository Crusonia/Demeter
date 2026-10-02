# Public clinical evidence: next admission decisions

Reviewed on 2026-10-02 for [#57](https://github.com/Crusonia/Demeter/issues/57)
and [#58](https://github.com/Crusonia/Demeter/issues/58). This is a source appraisal,
not an estimation protocol or accepted clinical input. The
[machine-readable record](validation/public-clinical-source-checkpoint-v1.json)
separates inspected content, acquired bytes and unresolved requirements.

The [iPOP working analysis](IPOP_A1C_WORKING_FIT.md) and
[predictive uncertainty supplement](IPOP_PREDICTIVE_UNCERTAINTY.md) are completed.
They describe a conditional laboratory process. More fitting of those same data
does not supply the missing clinical history, treatment, death or observation
process, or identify a dietary effect.

## New candidates and their limits

| Candidate | Inspected information | Admission decision |
| --- | --- | --- |
| [Söderberg et al., Mauritius](https://onlinelibrary.wiley.com/doi/10.1111/j.1365-2796.2004.01336.x) | Repeat surveys distinguish NGT, IFG, IGT and diabetes. Tables mix counts and standardized rates; incidence calculations assume midpoint dating and half-period censoring. Repeat-attender cohorts overlap. Potentially diagnosed-then-deceased people are excluded; a sensitivity assumes no diabetes among losses. | Require a verified source snapshot and compatible joint counts/timing with separate death and nonattendance dispositions. The inspected rates cannot substitute for that likelihood. |
| [Hamano et al., dietary crossover](https://dom-pubs.onlinelibrary.wiley.com/doi/full/10.1111/dom.15922) | Short inpatient menu periods in young untreated Japanese men; Table 3 reports fasting glucose, insulin and HOMA-IR. Endpoint and within-period-change comparisons use different paired/unpaired methods. Joint covariance was not verified. | Candidate for a separately frozen short-term menu-to-laboratory benchmark. No annual transition, remission, lag or UPF dose coefficient is identified. Participant data require a request. |

The [UMIN record](https://center6.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000056776)
discloses Hamano's registration after its listed last follow-up and reports an
enrollment count different from the paper. Preserve both sources without
inventing a reconciliation. This is not verified prospective registration.
Completion of the brief trial is not long-term death ascertainment.

[Louie's letter](https://doi.org/10.1111/dom.16044),
[Pereira et al.'s letter](https://doi.org/10.1111/dom.16063) and the
[author reply](https://doi.org/10.1111/dom.16138) are identified, but their substantive
text was not verified. Do not infer a criticism, concession or correction from
their references or metadata.

## What is verified, and what remains to do

The publisher representations were inspected. Exact-byte article requests
returned HTTP 403, so neither article has an acquired raw-byte pin in this
checkpoint. The official UMIN HTML was acquired and hashed; its receipt does not
verify the article or grant redistribution rights. Raw documentation remains in
ignored storage. No participant records or clinical numerical values were
intaken. Published outcomes were incidentally visible, so these are used sources,
not untouched validation targets.

Before a Hamano intake, verify immutable article/supplement bytes and reuse terms,
and resolve whether the correspondence changes the chosen contrast. Freeze exact
cells, units, endpoint-versus-change semantics, reported uncertainty, missingness,
sequence/carryover assumptions and disposition of nutrient differences. Keep any
published-result reproduction separate from a new causal estimate. Unknown
cross-period covariance cannot become independent clinical draws.

For progression/reversal, require compatible observed histories or sufficient
joint aggregates under the [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md).
Retain deaths, missed assessments, diagnostic history and treatment; specify the
observation/selection model and identify supported parameters before fitting.
Do not pool overlapping surveys or convert standardized incidence into an
annual transition probability.

This feeds I-01/I-05/I-07/I-11/I-12 and F-04/F-08 in the
[design registers](design/README.md). The health v0.1 target, population transport,
independent evaluation and scientific assessment remain required. No existing
evidence definition, equation, scenario, active parameter or release gate changes.
