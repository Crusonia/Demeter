# RFC-<issue-number>: <scientific change>

Copy this template to a new record; replace prompts with evidence or explicit
unresolved items. Do not leave a blank field that looks like approval.

- Status: proposed / accepted / rejected / deferred / withdrawn / superseded
- Issue and PR:
- Authors and date:
- Implementation: not started / partial / implemented; links and commit
- Scientific assessment: pending / scoped assessment linked below
- Scientific use: validation-only unless acceptance evidence states otherwise
- Supersedes / superseded by: none, or links

## Question and scope

Whose decision or research question? Population, geography, period and horizon?
Current phase, excluded mechanisms and unsupported interpretations?
Relevant Q-/RM-, L-/P-, X-, I-, F-, T- design IDs, or reasons not applicable?

## Relationship and alternatives

Exposure/intervention, outcome, comparator and estimand. Proposed causal path,
identification assumptions, confounding/selection/measurement issues and transport
limits. Include null and contradictory evidence, alternative mechanisms and what
would change the decision. Explain overlap/double-counting with existing paths.

## Evidence and parameter changes

| Key/source | Old value/status/grade/distribution | Proposed value/status/grade/distribution | Units, population and rationale |
| --- | --- | --- | --- |
| Replace with actual entries, or explicit unresolved evidence | | | |

Primary sources and exact locators, source vintage/retrieval/hash/terms,
transformations and uncertainty/dependence. Cite dataset receipts and parameter
registry records. Distinguish benchmark-only from active coefficients. Explain
each grade/distribution change and contradictory evidence.

## Equations and interfaces

Stocks, flows, units, ownership, operator order, time step, delays, bounds,
observation mapping and assumptions. Name exogenous/omitted quantities. Specify
module API compatibility and migrations if applicable. All substantive numeric
parameters must be registered; do not invent values to complete this form.

## Validation plan and results

Predeclared conservation, dimensional, extreme/null and alternative-structure
checks. Calibration/holdout windows and observation definitions; what evidence
would reject the proposal? Before/after settings, source/evidence hashes, seeds,
absolute/relative outcomes, uncertainty/sensitivity, residuals and regressions.
Distinguish planned tests from executed results. Keep failures visible.

## Conflicts and review

Author disclosures: relevant interests or none known.
Software reviewer/commit/scope/findings: identify actual review or pending.
Scientific reviewer/expertise/independence/disclosures/scope: actual review or pending.
Do not name someone as approving merely because they were requested to review.

## Objections and disposition

| Objection or alternative | Evidence/test | Response | Maintainer disposition and reason |
| --- | --- | --- | --- |
| Record unresolved matters; none only when assessed | | | |

Decision, decision-maker and review/PR links. Which claims remain unresolved?
What is approved for implementation versus scientific use? Rollback/migration
plan, compatibility impact and evidence that would trigger reconsideration.
