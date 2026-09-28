# New to Demeter?

Demeter is an open community project for exploring how food, health, agriculture,
and economics interact. We want people to be able to ask a question, inspect its
causal assumptions, run an experiment, and see what evidence would change the
answer. The model should become more useful as the community improves its parts.

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

## Questions a new reader should be able to answer

**What is the project trying to improve?** The quality of analysis: make causal
paths, feedback, delays, constraints, and uncertainty visible so people can test
their reasoning. Supporting a preferred Food is Health conclusion is not an
acceptance criterion. Evidence that contradicts a hypothesis belongs here.

**Who is it for?** Curious readers and contributors can begin with a guided
exercise. Researchers can inspect evidence and validation. Operators and policy
analysts can help define future decisions and constraints. No coding is needed
to ask a useful question or explain why a proposed mechanism might fail.

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

- Which person or organization makes the decision, and what can they control?
- What would they learn from a simulation that a static spreadsheet hides?
- Which time horizon and population matter, and who may experience different effects?
- Which feedback or delay could make an initially sensible decision disappoint?
- What observation would distinguish the proposed mechanism from a competing explanation?
- What evidence would justify moving from a learning exercise to decision support?

A future example is: if higher-quality food becomes more affordable, how much do
households substitute, can producers respond, and what health effects follow?
That is a connected research question in the roadmap, not a result of today's model.
