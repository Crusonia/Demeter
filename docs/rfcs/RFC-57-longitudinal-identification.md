# RFC-57: Identify progression and reversal before calibrating them

- Status: proposed
- Issue and PR: [#57](https://github.com/Crusonia/Demeter/issues/57), [PR #63](https://github.com/Crusonia/Demeter/pull/63); supports #56 and #1
- Authors and date: Codex-assisted work for the Food is Health-affiliated project, September 29, 2026 (UTC)
- Implementation: not started; no longitudinal fit or engine activation
- Scientific assessment: scoped source/identification appraisal below; external expert review pending
- Scientific use: validation-only; no clinical parameter promotion
- Supersedes / superseded by: none
- Maintainer disposition: pending; proposal status does not imply design acceptance

## Decision and boundary

Identify which transitions between defined glycemic observations can be estimated
in a supported population. This advances I-01 and I-07, L-00 and the health portion
of P-02 in the [design registers](../design/README.md). It does not close the
prevention-finance loops or establish a national PreChronic population.

The current cross-sectional benchmark supplies stock proportions. It cannot
uniquely identify progression, reversal and competing mortality. The
[existing clinical appraisal](../CLINICAL_EVIDENCE.md) explains why baseline-group
incidence and annualized follow-up percentages cannot simply replace current-state
hazards. [Issue #56](https://github.com/Crusonia/Demeter/issues/56) must also resolve
the observation/state contract; normal glycemia is not general metabolic health,
and controlled diabetes is not absence of a diabetes history.

## Candidate evidence routes

| Route | Useful evidence | Remaining constraint |
| --- | --- | --- |
| ARIC | Repeated examinations and event follow-up; current corrected aggregate benchmarks already appraised | Responsible investigator, permitted use, compatible visit-level fields and approved access; no dataset supplied |
| DPP/DPPOS | Randomized prevention interventions followed by repeated high-risk participant observations | Review the actual release dictionaries, observation schedule, diagnosis/treatment rules and attrition; selected trial participants do not identify national rates |
| Permitted published aggregate transition tables | Potentially sufficient if they retain initial/final categories, intervals, event denominators and joint uncertainty | Assess identifiability from the actual tables; marginals or endpoint incidence alone are insufficient |
| NHANES cross-sections and linked mortality | Population benchmarks and baseline-category mortality prediction | No repeated metabolic-state history; cannot identify the required reversal hazards |
| Chen 2018 and Okamura 2019 open releases | Verified original workbook identities and field-level inspection; Chen includes baseline/final glucose, Okamura includes baseline glycemia and incident diabetes | Neither release supplies the full treatment, post-diabetes and competing-death history; see the [source appraisal](../LONGITUDINAL_SOURCE_APPRAISAL.md) before proposing a narrower fit |

The [NIH DPP overview](https://www.niddk.nih.gov/about-niddk/research-areas/diabetes/diabetes-prevention-program-dpp)
documents the multicomponent lifestyle intervention and changed treatment after
the original trial. Those phases must be modeled separately; its intervention is
not a UPF-specific effect. The
[DPPOS repository listing](https://repository.niddk.nih.gov/study/40) advertises
requestable data. Listing metadata does not establish access or permitted reuse;
the full study page returned HTTP 403 during this appraisal.

The [BioLINCC FAQ](https://biolincc.nhlbi.nih.gov/faq/) describes registration,
research and ethics documentation, and an institutional research-materials
agreement. No application, agreement or message to a researcher has been submitted.
An available approved dataset or research partner is being requested from the
maintainer. This access constraint applies to that route, not to all possible
longitudinal evidence.

## Minimum useful intake contract

| Input | Required meaning and checks |
| --- | --- |
| Source identity and permission | Publisher/version, immutable hashes, authorized purpose, access restrictions, permitted aggregates and publication conditions |
| Cohort and selection | Recruitment population, inclusion/exclusion rules, geography, calendar period, age/sex definitions, sampling or design weights where applicable |
| Observation times | Relative visit times and units, missed visits and visit windows; preserve interval censoring rather than inventing event dates |
| Repeated measurements | Original glycemic values, units, assay changes, fasting validity and missingness; preserve raw observations separately from categories |
| Diagnosis and treatment history | Prior diagnosis, diabetes type if established, medication starts/stops, diagnostic confirmation and duration of control; no inferred remission from one low laboratory result |
| Intervention/exposure history | Assignment, actual exposure, adherence and cointerventions, including changes during extended follow-up |
| Competing events and follow-up | Death time or interval, last known contact, withdrawal, censoring reason and loss to follow-up |
| Validation partition | People, sites or periods withheld before estimating or choosing the model; no reuse of the mortality development/holdout work as independent state-transition validation |

Restricted raw records belong in approved local storage. The public repository
should contain permitted aggregate receipts, documented transforms and synthetic
software fixtures, not restricted participant records or credentials.

## Estimation contract before any fit

1. Inspect release documentation and eligibility coverage, then freeze the exact
   source version, observation definitions, exclusions and estimands. A protocol
   written after inspecting outcomes must be labeled as such.
2. Separate observation categories, diagnosed history and latent engine states.
   Decide whether direct observation is defensible. If an observation model is
   needed, identify its error parameters independently or show that the likelihood
   can distinguish them from transition rates. Otherwise leave them unresolved.
3. For interval-observed states, a candidate is a continuous-time competing-risk
   generator with nonnegative off-diagonal hazards, diagonal entries equal to the
   negative row sums, and death absorbing. Transition probabilities come from
   the interval-specific matrix exponential. This is a proposed likelihood, not
   an assumption that one such generator fits every age and treatment phase.
4. Retain simpler and alternative formulations. Check whether parameters are
   identified by likelihood profiles, information/rank diagnostics and recovery
   on labeled synthetic data. Do not select a model for producing a desired benefit.
5. Estimate supported-population hazards in reciprocal years and their joint
   uncertainty. Repeated observations from one person are not independent people.
   Evaluate attrition, treatment changes and observation-process assumptions.
6. Freeze the fitted model before independent prediction. Report state occupancy,
   transition/death counts, support and uncertainty in all prespecified domains;
   retain failures and unsupported domains. Clinical tolerance requires an explicit
   scientific rationale rather than a convenient post-result threshold.

National activation needs a separate age/sex, population and calendar-time
transport assessment. A fit in an older cohort or selected prevention trial cannot
silently initialize every U.S. age group. Population accounting, units, bounds,
reproducibility and before/after canonical outputs remain required.

## Current disposition

No new clinical values, evidence grades, equations or uncertainty distributions
are introduced. The [source appraisal](../LONGITUDINAL_SOURCE_APPRAISAL.md) now
records verified intake of two open workbooks and their field-level gaps. Chen's
baseline/final glucose could support a restricted analysis under an explicit
observation/censoring model; neither release completes the requested dynamics.
No fit has been performed. The next concrete action is to obtain a permitted
package with the missing histories, or identify sufficient compatible aggregate
evidence, then freeze the estimable likelihood and validation partition. #57
stays open; an incidence benchmark would not close it.
