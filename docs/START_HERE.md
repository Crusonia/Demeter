# New to Demeter?

Demeter is an open community project for participants throughout the agriculture,
food, and health value chain. Its purpose is to help each participant understand
the value added by changes in the system: what they can change, how the effects
reach other participants, and what enables them to capture a share of the value.
The model should become more useful as the community improves its parts.

The ambition is large. Each contribution should be small enough to understand,
test, and review. You do not need to understand the whole future system to help.

## A management flight simulator, built over time

Think of the learning approach associated with John Sterman and MIT's
[management flight simulators](https://mitsloan.mit.edu/faculty/academic-groups/system-dynamics/courses-and-programs):
make a decision in a simulated system, observe delayed consequences, and revise
your understanding of how the system behaves. This is an inspiration for Demeter's
learning design, not a claim of MIT affiliation or a reproduction of an MIT model.

For Demeter, a useful exercise asks: what did we expect, what happened under the
specified assumptions, what mechanism produced it, and what would we need to
observe before trusting that mechanism in the world? A failed hypothesis or an
important missing dataset can be a valuable result.

The current program is the first set of working instruments: a health model,
inspectable evidence, experiments, and an offline report. A broader interactive
decision simulator is a later phase. We will earn that scope through validation.

## What can I do now, and what comes later?

The flagship future exercise is a [shift toward real food](REAL_FOOD_VALUE_CHAIN.md).
A participant should learn the levers connecting agriculture, food, and health.
For example, how could a producer's regenerative practice create value at retail,
and how much could return to the producer? On the health side, could targeting
people at earlier metabolic risk—the proposed PreChronic population—reduce net
healthcare costs? These are questions the staged model is being built to test.

| Stage | What it contributes | Status |
| --- | --- | --- |
| Foundation and Phase 1: health | Trace exposure through metabolic states, mortality, and life tables; test conservation, evidence, uncertainty, and historical comparisons. | Software runs. Scientific v0.1 is incomplete. |
| Phase 2: agriculture and supply | Investigate production response, capacity, land, and farm economics. | Planned after the health acceptance gate. |
| Phase 3: behavior and adoption | Represent different household, farmer, and company responses where differences materially affect results. | Planned; agents are used only when needed. |
| Phase 4: healthcare economics and policy | Follow spending, incentives, and feedback into food choices and production. | Planned. |
| Phase 5: integrated system | Connect modules while carrying uncertainty and testing their interfaces. | Planned. |
| Phase 6: decision simulator | Make tested experiments accessible through an interactive application. | Planned; today's HTML is a diagnostic report. |
| Ongoing governance (Phase 7 in the roadmap) | Review evidence updates, model revisions, and reproducible releases. | Contribution and provenance practices start now. |

The [program vision](PROJECT_VISION.md) is the canonical roadmap. The
[system architecture](SYSTEM_ARCHITECTURE.md) describes the intended modules;
the [scenario catalog](SCENARIO_CATALOG.md) describes future experiments.
Neither document means those capabilities already exist.

Three companion pages frame the whole program. The [top-level metrics](wiki/Top-Level-Metrics.md)
define how scenarios are judged: healthy longevity, health-adjusted productivity,
and health-inclusive GDP, at macro and industry level, with a climate guardrail.
The [stakeholder rigidities](wiki/Stakeholder-Rigidities.md) list the beliefs that
a better, cheaper system is impossible and how the model would test each one.
[Related work](RELATED_WORK.md) shows which existing models Demeter builds on and
where it differs.

For the reasoning behind a proposed mechanism, use the [design inputs](design/README.md):
a table of causal loops, a register of positive and negative externalities,
and the inputs/equations/tests needed to evaluate them. These are hypotheses to
inspect and improve, not a list of established benefits.

## Questions a new reader should be able to answer

**What is the project trying to improve?** The quality of analysis: make causal
paths, feedback, delays, constraints, and uncertainty visible so people can test
their reasoning. Supporting a preferred Food is Health conclusion is not an
acceptance criterion. Evidence that contradicts a hypothesis belongs here.

**Who is it for?** Every element of the value chain: farmers and their suppliers,
processors, food companies, distributors, retailers, households, clinicians,
providers, payers, employers, public programs, and capital providers. Each should
be able to explore its own decisions within the same connected system. Researchers
and community contributors help make those pathways testable. No coding is needed
to propose a decision, identify a constraint, or challenge a mechanism.

**What does "value" mean here?** Report it for a specific participant. Retail
sales, farmer margin, household health, and payer savings are different outcomes.
Trace the costs and payment arrangements connecting them. Adding a feature such
as a regenerative practice does not automatically mean its creator captures a
retail premium or a health benefit; the model should help investigate when that
connection exists and when it fails.

**What does the real-food exercise need to define?** The foods and quantities that
replace the reference basket, actual intake, access, affordability, and relevant
product attributes. "Real food" is the direction of inquiry; an executable scenario
needs measurable inputs. Likewise, PreChronic requires validated earlier-risk
inclusion criteria. Neither term supplies an assumed health effect or cost saving.

**Why start with health if the goal spans agriculture and economics?** One complete,
testable causal path is a foundation for linking modules. A broad model with
unsupported links would make its apparent precision harder to assess. The current
boundary is a sequencing choice; the long-term purpose remains systems analysis.

**Are the numbers real?** Some are observed government data, some are derived,
and important metabolic and dietary parameters are still synthetic validation
inputs. The [evidence registry](../evidence/README.md) labels their status.
Current diet-induced longevity differences are not scientific findings.

**What would count as progress?** A verified source, a better state definition,
a reproducible transform, a meaningful holdout test, a clearer explanation, or a
documented failure can all advance the model. More modules or a more attractive
chart alone do not demonstrate progress. See [current acceptance status](V0_1_STATUS.md)
and [evidence gaps](EVIDENCE_GAPS.md).

**Do we have to wait for the entire model?** No. Each stage should provide useful
learning and inspectable tools within its stated limits. Today you can reproduce
the health mechanics and challenge their assumptions. Future stages add questions
only as their mechanisms and evidence become supportable.

**Where are the data, and can I reproduce a run?** The repository includes a
[curated source archive and data guide](../data/README.md), model-ready bundles,
evidence metadata, scenarios, a dependency lockfile, and tests. Raw sources remain
distinct from transforms and outputs. A source being present does not establish
that it measures the causal quantity the model needs.

**Who decides what gets included?** Anyone may propose an issue or pull request.
Carter Williams (@jcarterwil) reviews and merges changes. Scientific changes must
document their evidence and validation; a merge is not scientific certification.
See [governance](../GOVERNANCE.md) and [contributing](../CONTRIBUTING.md).

## Start with one experiment

1. [Install and run](GETTING_STARTED.md) on macOS, Linux, or Windows.
2. [Try the first exercise](FIRST_EXERCISE.md): predict, compare, inspect, and debrief.
3. Bring one observation, confusing explanation, or evidence gap to an
   [issue](https://github.com/Crusonia/Demeter/issues/new/choose).

## Questions that should shape future exercises

These are open design questions, not settled model features. Contributors can
help answer them in issues before proposing implementation:

- For each participant, what can they change and what mechanism lets them capture value?
- Which specific food basket and substitutions define the real-food transition?
- Which earlier-risk population and intervention define the PreChronic comparison?
- What would they learn from a simulation that a static spreadsheet hides?
- Which time horizon and population matter, and who may experience different effects?
- Which feedback or delay could make an initially sensible decision disappoint?
- What observation would distinguish the proposed mechanism from a competing explanation?
- What evidence would justify moving from a learning exercise to decision support?

The [flagship brief](REAL_FOOD_VALUE_CHAIN.md) brings these questions into one
learning sequence: choose a role, predict the effects of a lever, trace value
through the chain, inspect the health/cost pathway, and identify the next evidence
that would improve the decision. It describes the destination of the staged model.
