# Public observations needed for progression and reversal

Assessment date: October 1, 2026 UTC. Supports
[#57](https://github.com/Crusonia/Demeter/issues/57),
[RFC-57](rfcs/RFC-57-longitudinal-identification.md) and the
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md).

Demeter can now evaluate a declared longitudinal likelihood. Its
[software exercise](LONGITUDINAL_LIKELIHOOD.md) uses synthetic observations;
clinical progression and reversal remain unresolved. The next contribution
needed is compatible public evidence, rather than another software example.

For a newcomer: a follow-up glucose result tells us where someone was measured
at that visit. It does not tell us every change between visits. Someone with a
later low glucose result may still have a diabetes diagnosis and be taking
medication. People who died or missed testing cannot be silently counted as
unchanged. We need enough linked observations to distinguish these explanations.

This document makes the existing contract concrete for source discovery. It
changes no equation, likelihood, clinical threshold, evidence parameter or
scientific acceptance criterion. It feeds the observation and validation inputs
I-11/I-12 and formulation F-08 in the [design registers](design/README.md).

## What to propose

Open an [evidence issue](https://github.com/Crusonia/Demeter/issues/new/choose)
with the primary publication or repository link, exact release and relevant
table or variable names. Describe which observations are actually available,
the reuse terms and known gaps. A link and an explanation are enough to begin;
do not post individual health records in an issue or commit them to Git.

Two possible routes follow. Neither guarantees identification: the proposed
observables must be checked against the chosen model before fitting.

| Route | Needed public material | What would not replace it |
| --- | --- | --- |
| Linked records in a permitted release | A pseudonymous linkage key, entry information, repeat measurements and actual visit times, retained diagnosis/treatment history, and death/contact/withdrawal information; a dictionary explaining codes, selection and missingness | Blank questionnaires, a baseline-only table, or a workbook containing only an incident-diabetes flag |
| Sufficient published aggregates | Joint observation-pattern counts and their time schedules, or source-justified sufficient statistics for a specified observation model; eligible denominators, selection and missingness definitions, and the applicable death/history/treatment information | Separate visit marginals, mean follow-up, odds/hazard ratios or marginal intervals without the information needed for that likelihood |

## Records and definitions to resolve

| Information | Specific source requirement |
| --- | --- |
| Source and permission | Publisher, release/version and corrections, downloadable artifact or exact aggregate table, citation, reuse/output terms. Open article access alone does not establish participant-data access or redistribution permission. |
| Population and entry | Recruitment, eligibility/exclusions, age/sex, geography and period, entry/time origin, baseline measurements, prior diabetes diagnosis/type and treatment. Preserve unknown categories and sampling/selection information. |
| Glycemic measurements | Assay, units, fasting/test conditions, collection time or supported interval, quality and missing codes. Supply the source diagnostic algorithm/version and confirmation rules; do not introduce an unsourced cutoff. |
| Repeated observations | Preserve which measurements belong to the same person, their order and times/windows. Distinguish collection, result, trigger and confirmation dates, as well as scheduled visits from visits prompted by symptoms. |
| Diagnosis and treatment | Preserve prior and incident diagnosis, medication starts/stops and available duration. A later lower measurement retains diagnosis history; remission requires an explicit source definition and supported treatment-free duration. |
| Events and stopping | Last negative test, first positive test, confirmation, last glucose assessment, last contact and administrative end. Recorded detection is not automatically biological onset; exact and interval times remain distinct. |
| Death and attrition | Death status/time or supported interval, withdrawal/loss reasons and eligible denominators. Preserve deaths, unassessed survivors and unknown status separately where the source supports it; unresolved categories remain unresolved. |
| Dependence and uncertainty | Survey design/weights when applicable, repeated participants, overlapping reports/shared controls, measurement uncertainty and any published covariance. Do not manufacture joint uncertainty by assuming marginal intervals are independent. |
| Evaluation | Independent compatible observations, their population/time resolution and any prior use. If unavailable in a proposal, leave the independent-evaluation requirement open. Freeze selection, likelihood, alternatives, uncertainty and evaluation plans before inspecting reserved outcomes. |

Missing exact onset dates do not automatically disqualify a source. Interval
events or panel visits can support a likelihood with an adequate observation
and stopping model. Unknown treatment, timing, selection or death cannot be
resolved merely by declaring an assumption in the software contract. Any working
assumption needs a source appraisal, alternatives and a restricted interpretation.

## When aggregate tables can be enough

For a fully observed Markov panel with justified sampling, consecutive-pair
counts grouped by visit schedules, covariates and regimes can supply its transition
likelihood. Repeated pair tables share participants; they are not independent
binomial experiments. With latent/coarsened states, complete linked
observation-pattern counts may be needed instead. A single prediabetes-start
endpoint row cannot be assumed to identify all rates; test identification.

For continuously observed, time-homogeneous transitions under an appropriate
sampling/stopping model, transition counts and time at risk in each state can be
sufficient. Total or median follow-up cannot replace state occupancy, unobserved
transitions or competing events. These grouping requirements follow from the
panel, exact-transition and coarsened-path likelihoods in the
[primary msm manual, section 1.4](https://cran.r-project.org/web/packages/msm/vignettes/msm-manual.pdf).
They do not establish source eligibility. Do not digitize bar heights or fabricate
individual histories from margins.

Keep joint covariance when published. Otherwise regenerate uncertainty from a
justified observation likelihood or report the unresolved dependence and supported
bounds. A point estimate, an interval or a full transition-probability matrix by
itself does not establish the likelihood or permit conversion into engine flows.
The continuous-time evaluator and the annual simulation operator remain separate.

## New source search: observed gaps

This was a bounded methods/access appraisal, not numerical intake. Search results
and article rendering incidentally exposed published outcomes. These are used
sources; a later selected-cell reproduction cannot be called an untouched
holdout. No participant data were acquired, count cells selected or effects
calculated. The links identify primary sources; the
[versioned receipts](validation/public-longitudinal-source-receipts-v1.json)
pin the inspected documentation described below. These are documentation
metadata, not empirical parameter entries. Full publications are not redistributed.

| Candidate and exact locator | Observed public surface | Current disposition |
| --- | --- | --- |
| [AusDiab official report](https://www.baker.edu.au/-/media/documents/impact/ausdiab/reports/ausdiab-report-2005.pdf?la=en), glycemia chapter, mortality methods and attendance appendices; [access protocol](https://baker.edu.au/-/media/documents/impact/ausdiab/ausdiab-data-access-form.pdf?la=en) | FPG/OGTT and medication definitions, death-register linkage and separate examination/telephone follow-up. The pinned protocol requires application, ethics and undertakings for records. | No full glycemic joint matrix located in the inspected report inventory. Separate incidence/mortality summaries and a common-duration incidence calculation do not supply jointly timed paths. |
| [CARDIA analysis (2025)](https://doi.org/10.1038/s41598-025-19472-y), Research design and methods, Figures 1–3; [BioLINCC catalog](https://biolincc.nhlbi.nih.gov/studies/cardia/) | Repeated examinations and diagnosis history. Inspected figures summarize cardiovascular-health trajectories/associations. BioLINCC requires registration/request and has tiered commercial consent. | No sufficient timed glycemic-path/death table located in the inspected main article. Supplemental measurement tables were not inspected; actual record coverage remains unverified. |
| [Paprott et al. (2018), Germany](https://onlinelibrary.wiley.com/doi/10.1155/2018/5703652), Methods §§2.1–2.5, Figure 1, Data Availability | Selected baseline-prediabetes participants followed to glycemic categories; diagnosed history and survey weighting are distinct. Records are nonpublic, with secure on-site access by request. | One selected starting row does not automatically identify both progression and reversal plus death. Variable intervals, survey weighting and incomplete follow-up cannot become an iid clinical likelihood without further evidence. |
| [ODCDC (online 2025)](https://link.springer.com/article/10.1007/s00125-025-06555-8), Methods, ascertainment, sensitivity analyses, Data availability; supplementary Table 3 and Figures 1–2 | Repeated assessments, retained prior-diabetes criterion and confirmation/competing-death sensitivity analyses. Individual records are nonpublic under cohort governance. Public timing summaries are cohort medians; diagrams describe classification and pooling/selection. | Strong methods lead, with no sufficient jointly timed glycemic/death/missingness observations verified. Median visit intervals, classification flows and fitted subhazard ratios do not replace linked paths. |
| [Geelong men, Harland et al. (2025)](https://onlinelibrary.wiley.com/doi/10.1155/jdr/9926306), Methods §§2.1–2.3, Figure 3, Data Availability Statement | A baseline/follow-up glycemic-label Sankey; labels combine FPG, self-report and medication. Study baseline mixes original and later waves. Some or all datasets are nonpublic, available by author request. | Candidate for conditional observed label distributions. Actual durations, survival/assessment selection, retained diagnosis history and treatment chronology remain inadequate for treating the displayed matrix as a clinical transition kernel. No counts extracted. |
| [Project Baseline Health Study (2022)](https://link.springer.com/article/10.1186/s12933-022-01565-x), Methods, discussion limitations, Availability of data and materials | Annual HbA1c/random-glucose, history and medication categories; no fasting glucose or OGTT. The publication describes committee-reviewed external applications. | No unrestricted linked release or sufficient joint observations verified. Useful observation-design reference; does not unblock fitting. |
| [Jinchang worker cohort (2023)](https://doi.org/10.1093/eurjpc/zwad196), Methods, discussion limitations, Data availability | Repeated examinations and a published multistate model. Underlying data are author-request only. The model excludes all-cause mortality and some reverse transitions; additional drug information would be needed. | Published transition summaries are a possible model comparator, not sufficient observations to refit Demeter's requested clinical dynamics. No estimates extracted or converted into active rates. |
| [CRONICAS CRP/mortality subset, version 1](https://api.figshare.com/v2/articles/17129321/versions/1); separate [Dictionary.txt](https://ndownloader.figshare.com/files/31671035), fields `code`, `db5`, `death`, `tseg_years` and CRP categories | CC BY 4.0 release; only metadata and the separately designated dictionary were inspected. The dictionary documents a composite diabetes label, death and follow-up years; repeated categories concern CRP. | No documented glycemic measurement series, collection clocks, separate diagnosis/treatment history or contact/loss reasons. Participant CSV was not fetched. This subset cannot supply the requested glycemic progression/recovery likelihood; no conclusion is drawn about the fuller cohort. |

## Pinned documentation versions

The [receipt artifact](validation/public-longitudinal-source-receipts-v1.json)
records requested/resolved URLs, actual retrieval times, media/status, cache
filenames, sizes, SHA-256, rights and inspected locators. All successful cached
documents were checked against those sizes/hashes before this artifact was saved.
Original AusDiab, German, CARDIA and ODCDC downloads retain their original
timestamps. Other receipts are fresh saved acquisitions after earlier web or
in-memory inspection; they are not reconstructed original downloads.

The Geelong XML and Jinchang HTML came from separate successful official public
routes after publisher requests failed. Their qualitative methods/access
statements were checked against those acquired documents. CRONICAS's new saved
metadata/dictionary hashes match the earlier in-memory observations. Failed
publisher/metadata requests and the unacquired AIHW page remain failed receipts;
they do not establish publication content or clinical-data availability.

Full documents stay in ignored download storage. Fetch each recorded URL
separately if needed and compare the exact bytes with its receipt; keep changed
upstream versions separate and leave a mismatch unresolved. A dynamic HTML page
can change without a scientific revision. Matching bytes check provenance,
not clinical validity, record coverage or permission to obtain participant data.
The original ODCDC masking failure and incidental numerical exposure remain
recorded; no blinded inspection claim is made.

`uv run demeter data verify-packages --check-tracked` verifies the committed
receipt artifact's checksum offline. It does not fetch or verify these optional
full-document downloads. The appraised documentation has no evidence-registry
parameter or clinical source-package activation.

## Scope and next decision

The [Stanford iPOP source appraisal](IPOP_SOURCE_COVERAGE.md) adds a concrete
repeated-laboratory lead with commit-pinned code, selected header metadata and
Table S0 measure-name bindings. Its [receipts](validation/ipop-schema-receipts-v1.json)
record actual partial/full acquisition, failed attempts and limited inspection.
Subsequent review of Zheng et al. (2022) establishes public provenance for the
named derivative. The next step is a frozen linked-panel intake with explicit
measurement and relative-day assumptions, preserving unknown upstream rawness,
specimen association and record coverage. No clinical fit or empirical hazard was
admitted; the access correction does not resolve diagnosed history or mortality.

The subsequent [source-admission appraisal](PUBLIC_LONGITUDINAL_ADMISSION.md)
adds Dryad occupational examinations and SLIMM-T2D as conditional leads, plus
live CRELES and Comorbidities rights/access decisions. It records a finite
usage-document/schema gate and successful source-byte receipts separately from
failed downloads; it admits no clinical fit or participant acquisition.

The bounded search above does not establish that no suitable public source
exists. Access restrictions concern the inspected releases; an author's fuller
dataset may contain observations absent from a publication. No access application,
account registration, agreement acceptance or researcher outreach was made.

An eligible candidate first receives an immutable source/rights receipt and a
frozen source-specific estimation protocol. Only then should selected quantities
be captured and fitting attempted. Keep source reproduction, fit diagnostics,
independent prediction and national transport as separate assessments. Unidentified
hazards stay unresolved and simulations remain validation-only.

For [#58](https://github.com/Crusonia/Demeter/issues/58), linked glycemic evidence
alone is insufficient. A food pathway also needs a defined exposure/dose,
intervention/comparator, response timing, cointerventions, causal or associational
interpretation and appropriate evaluation. This intake requirement does not close
#57, #58, the [v0.1 objective](CODEX_V0_1_OBJECTIVE.md) or milestone #27, and does
not authorize later agriculture, economics or investment conclusions.
