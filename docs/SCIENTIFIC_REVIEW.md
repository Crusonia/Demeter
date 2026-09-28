# Scientific contributions and evidence review

Demeter must support competing explanations, null results and challenges to the
Food is Health thesis. A review asks whether a claim is well specified and tested,
not whether it supports the project's originating thesis. Scientific meaning,
software correctness, design approval and permission to merge are distinct.

## Choose the review path

| Change | Required record |
| --- | --- |
| Typo, explanation, setup fix or refactor with unchanged semantics | Ordinary PR, scope and relevant verification |
| New causal relationship, state definition, exposure mapping, outcome, lag, observation model, calibration method or material structural alternative | Scientific RFC linked to an issue and implementation PR |
| Evidence source/value/vintage, grade, distribution, bounds or transport decision | Evidence-change record in the PR; use an RFC if interpretation or behavior changes materially |
| Major architecture, module interface, time-step, engine, persistence or compatibility decision | ADR; also an RFC when scientific semantics change |

Use the [RFC template](rfcs/TEMPLATE.md) and [decision process](decisions/README.md).
A small evidence correction can use the PR rather than a separate RFC, but still
needs the complete before/after evidence record below. Do not use a refactor label
to hide changed arithmetic, units, operator order or interpretation. A benchmark
addition that does not drive the model must say so explicitly.

## Responsibilities and review outcomes

| Role | Responsibility |
| --- | --- |
| Author | Define the estimand, scope and alternatives; supply source receipts, reproducible changes, uncertainty, conflicts and unresolved questions. Respond to objections without erasing them. |
| Software reviewer | Inspect implementation, invariants, reproducibility, source integrity, permissions and tests. Report exactly what was exercised; passing code is not clinical validation. |
| Scientific reviewer | Identify relevant domain/method expertise; assess design, causal identification, population/endpoint alignment, uncertainty, transport and validation. State limits of the review and conflicts. |
| Maintainer (Carter Williams) | Decide phase/scope and merge, request appropriate review, record disposition and unresolved objections, preserve the release boundary and enforce project conduct. Merge authority is not scientific expertise. |

One person may hold multiple roles, but must label each assessment separately and
must not call their own review independent. Automated tools and AI can assist;
they are not named human scientific reviewers or evidence of independent review.
Do not attribute approval to someone who only commented or was asked to review.

Each material PR records these four lines, with links or an explicit absence:

- **Software assessment:** reviewer, commit, checks and findings; or not reviewed.
- **Scientific assessment:** research-backed validation report and/or reviewer,
  expertise/scope, evidence and disposition; or pending/not performed. State
  whether external expert review is pending and whether any review is independent.
- **Merge disposition:** maintainer decision and reason; PR merge is the authority.
- **Scientific use:** validation-only, or the specific accepted scope with the
  acceptance evidence. Do not infer release readiness from a merged PR.

A maintainer may merge bounded experimental mechanics or benchmark-only work
while expert review is pending, provided unresolved evidence stays explicit,
outputs remain validation-only and release gates stay closed. Such a merge is
not scientific acceptance. Material scientific claims or removal of a release
blocker require a documented assessment and acceptance evidence for the exact
claim. That assessment may follow the research-backed report path below without
first recruiting a human reviewer. Missing evidence, unmatched populations or
endpoints, and failed validation remain substantive blockers. These process records do not add mandatory GitHub
approval votes or alter [branch protection](../GOVERNANCE.md).

## Research-backed validation report path

Carter Williams approved this path on September 28, 2026. This adds a route to
scope-limited scientific assessment without a named human reviewer. Experimental
work was already permitted while expert review was pending; reviewer recruitment
must not be treated as a prerequisite for implementation or predeclared evaluation.
This does not turn an automated report into independent human review or waive
the original issue's acceptance criteria.

Use the [ISPOR–SMDM transparency and validation framework](https://pubmed.ncbi.nlm.nih.gov/22999134/)
to distinguish code verification, expert assessment, comparison with other
models, external validation and predictive validation. A framework is guidance,
not evidence that a particular Demeter claim is correct.

The report must:

1. Map each claim/mechanism to primary evidence, exact estimand, population,
   units, study period, uncertainty and causal/associational status. Record
   competing/null evidence and unidentifiable quantities.
2. Reproduce applicable published benchmarks with pinned data, code and receipts.
   State what each reconstruction checks and which targets were used for fitting.
3. Freeze observation definitions, models, alternatives, evaluation metrics and
   any justified acceptance thresholds before inspecting reserved outcomes.
   If no defensible clinical tolerance exists, report predictive diagnostics
   descriptively and keep clinical acceptance unresolved; do not invent a cutoff.
4. Test independent data where available, retain failures, compare structural
   alternatives, and separate numerical, sampling and structural uncertainty.
5. Record exact checks and results, scope-limited conclusions, unresolved gaps,
   conflicts, authorship, and **external expert review pending** when applicable.
   AI-assisted critique is labeled automated; it is not independent human review.

Implementation, evidence collection, preregistration and descriptive validation
may proceed while external review is pending. A maintainer may accept a supported
scope based on this record, with a linked disposition and unchanged evidence
standards. Passing a mortality prediction test does not validate a dietary causal
pathway or satisfy the whole v0.1 objective. Neither the report nor a reviewer's
signature can replace missing observations or justify unsupported transport.

## Adding or changing a causal relationship

Before coding, the RFC specifies the question, decision-maker, population,
geography, time horizon and phase. Trace relevant Q-/RM-, L-/P-, X-, I-, F- and
T- IDs from the [design registers](design/README.md); mark genuinely inapplicable
IDs rather than inventing a link. An RFC/design premise is not an evidence status.

Record the exposure/intervention, outcome, comparator and estimand. Separate
association, causal identification, mechanism and modeling assumption. Describe
confounding, selection, missingness, competing risks, reverse causality, diagnostic
changes and transport limits as applicable. Include contradictory/null evidence
and explain source inclusion/exclusion. Publication or an official data source
does not establish that a particular causal coefficient is identified.

Write inspectable equations, units, stock ownership, competing flows, operator
order, delays and supported exposure ranges. Name overlaps with existing pathways
and how double counting is avoided. Identify what stays exogenous and what is
omitted. Unknown effects remain unresolved, not silently zero. A structural null
may be an explicitly labelled hypothesis without claiming an empirical zero.

Predeclare tests that could reject the mechanism: conservation/bounds and extreme
conditions, dimensional checks, reference/null equivalence where justified,
alternative structures, uncertainty and held-out behavior. Define observation
mappings and split calibration from holdout data before fitting; retain failures
and discrepancies. Do not tune to a desired food, commercial or policy conclusion.
Do not increase model complexity without a documented mechanism or validation need.

## Evidence-change record

For each affected parameter or dataset, include:

1. Old and proposed value, units, evidence status, grade, uncertainty, bounds,
   registry key and model role; list affected scenarios/equations/outcomes.
2. Publisher, primary source URL/DOI when available, exact table/figure/page or
   API query, release/vintage, retrieval date, checksum and reuse terms. Record
   corrections/retractions. Never invent missing bibliographic details.
3. Population, geography, study period, exposure and endpoint definitions,
   sampling/measurement method, and applicability or unresolved transport gaps.
4. Reproducible extraction/transformation, including denominators, survey weights,
   unit/risk conversions, aggregation and any missing-data rules. Keep source
   snapshots immutable and derived/model-ready data separate.
5. Rationale for the change, competing evidence and uncertainty implications;
   a source update is not an automatic promotion from benchmark to engine input.
6. Before/after canonical scenarios under the same settings, hashes and seeds;
   absolute/relative differences, uncertainty/sensitivity and historical residuals
   where applicable. Report both improvements and regressions, plus limitations.

Use the [data policy](../data/README.md) for storage, licensing, restricted inputs
and offline reloads. Never add identifiable health records or credentials. When
data cannot be redistributed, document the restriction and a reproducible access
or supported alternative path; a missing source is not a passing validation.

## Grades, distributions and calibration

Registry **status** (`synthetic`, `estimated`, `observed`, `derived`) describes
provenance, not causal strength. **Grade** A–E is separate evidence metadata;
synthetic parameters require E. Use the [registry definitions](../evidence/README.md) and
[clinical appraisal](CLINICAL_EVIDENCE.md), not a new informal grading scale.

A grade change names the old/new grade, source quality, identification and
applicability rationale, conflicting evidence and reviewer disposition. An
observed association does not become causal because its effect is large or its
fit improves. Keep disagreements visible; do not multiply grades by effect sizes.

A distribution change names its source/estimand and whether it represents
sampling, parameter, scenario or structural uncertainty. Document support,
units, dependence, transformations and truncation, plus prior/posterior and
calibration data when applicable. An interval or survey SE is not automatically
a sampling distribution for a causal effect. Fixed values require a rationale;
narrowing uncertainty to obtain a desired result is unacceptable. Preserve joint
draw identity and correlations rather than silently resampling shared inputs.

Changing a parameterization after seeing a holdout result must be disclosed.
That holdout is then used evidence, not a fresh independent test. Record a new
validation plan and known failures before claiming improved generalization.
Code tests and a reviewer signature do not replace the model's scientific gates.

## Conflicts and disagreement

For material model/evidence changes, authors and reviewers disclose relevant
employment, funding, advisory roles, equity/product interests, involvement in the
source research, or other relationships that could affect judgment. State
**none known** when applicable; disclose enough context to assess the conflict,
not private financial amounts or unrelated personal information. Maintain the
disclosure as the proposal changes. Maintainers follow the same rule.

An interest is not automatic exclusion. A material reviewer conflict must not be
presented as independent review; seek an unconflicted assessment or retain an
explicit scientific limitation. If a needed disclosure is unavailable, record
that limitation rather than assuming no conflict. Project affiliation with Food
is Health is disclosed by the [vision](PROJECT_VISION.md), not proof of validity.

State each unresolved objection as a testable claim, source issue or scope
disagreement, with the author's response and maintainer disposition. Retain
minority views and reasons for rejecting/deferring a proposal. Reopen a decision
when new evidence or a failed test changes its basis; use a superseding RFC/ADR
instead of rewriting history. Conduct complaints follow the
[code of conduct](../CODE_OF_CONDUCT.md), not a vote on the scientific hypothesis.
