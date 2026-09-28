# Demeter: an open Food is Health model

**Demeter is an open-source project under the [Food is Health Substack](https://foodishealth.substack.com/) to model the market dynamics connecting food, agriculture, health, and capital.**

Our central question is: **When the economics of food and health change, which levers matter, where does value move, and which choices become worth making?**

The intended users are participants at every stage of the value chain. Each
should be able to explore how a feature or action they add creates value elsewhere
and what enables them to capture a share. A producer tracing a regenerative
practice's potential value through retail is one example.

The flagship future exercise is a [shift toward real food](../REAL_FOOD_VALUE_CHAIN.md).
It focuses learning on the levers connecting agriculture, food, and health, and
on whether earlier intervention in the proposed PreChronic population can reduce
net healthcare costs. Commercial returns and health savings remain questions to
test through the staged model and its evidence requirements.

Food is Health explores ideas about that changing system. Demeter aims to make the underlying hypotheses inspectable: identify the mechanism, attach evidence, model the delay, test competing explanations, and show what would change our conclusion. Contributions that overturn an appealing hypothesis are valuable.

## Why model a connected market?

Actors in separate industries usually see only their own accounts. Demeter's purpose is to make the coupling visible: how a change in agriculture, food, health care, climate, research, or capital reaches the others, where improvements reinforce each other, where they trade off, and who bears or captures the value. Representative couplings include food and climate, chronic and acute disease, and microbiome research and agriculture. Each is a hypothesis to test, including the possibility that the spillover is negative.

A lower food price matters through what households actually buy and eat. A health improvement matters economically through utilization, payment contracts, and who remains responsible for a population long enough to benefit. A demand shift matters to agriculture through margins, processing capacity, land, and the time required to change production.

These connections can reinforce change or absorb it. A local intervention can create a bottleneck elsewhere. A large social benefit can coexist with weak incentives for the organization asked to fund it. Demeter is being built to make those relationships explicit.

## What we want to learn

- **System levers:** which feasible actions change outcomes, through which pathways, at what cost, and over what time horizon?
- **Changing trends:** how would different paths for food affordability, treatment access, consumer preferences, technology, and reimbursement alter the system?
- **Value distribution:** who gains health, saves money, earns revenue, bears transition costs, or loses an existing source of income?
- **Strategic options:** when is it useful to pilot, learn, wait, expand, switch, or exit—and what could make that opportunity expire?
- **Evidence priorities:** which unresolved relationship could change a decision enough to justify further research?

## Read the guide

New contributors can begin with the [plain-language introduction](../START_HERE.md),
[macOS/Linux/Windows setup](../GETTING_STARTED.md), and
[first learning exercise](../FIRST_EXERCISE.md). Demeter adopts a management-flight-simulator
learning approach: predict, experiment, inspect the mechanism, and debrief.
The larger model grows in validated stages. [Source datasets](../../data/README.md)
and [the PR process](../../CONTRIBUTING.md) are part of that shared foundation.

| Page | What it covers |
| --- | --- |
| [Real-food value-chain scenario](../REAL_FOOD_VALUE_CHAIN.md) | The flagship future exercise: decisions, value creation/capture, regenerative-to-retail pathways, and PreChronic prevention. |
| [Model-design inputs](../design/README.md) | Causal-loop and externality tables, input requirements, and formulation/tests that turn premises into reviewable model design. |
| [Top-level metrics](Top-Level-Metrics.md) | Healthy longevity, health-adjusted productivity, and health-inclusive GDP at macro and industry level, with a climate guardrail. |
| [Stakeholder rigidities](Stakeholder-Rigidities.md) | Beliefs that a better, cheaper system is impossible, which are real, and how the model tests them. |
| [Related work](../RELATED_WORK.md) | Existing models and flight simulators, and where Demeter fits. |
| [Market dynamics](Market-Dynamics.md) | Stocks, flows, feedback, prices, incentives, delays, and value distribution. |
| [Levers and scenarios](Levers-and-Scenarios.md) | Actionable controls, external trends, causal pathways, and experiments. |
| [Real options and strategic value](Real-Options-and-Strategic-Value.md) | Contingent decisions, trigger conditions, learning, downside, and value capture. |
| [Visualization and tornado diagrams](Visualization-and-Tornado-Diagrams.md) | Which assumptions move an outcome, in which direction, and which could change a decision. |
| [Evidence and model status](Evidence-and-Model-Status.md) | What runs today, what remains unresolved, and standards for credible results. |
| [Contributing](Contributing.md) | How to add evidence, challenge assumptions, propose scenarios, or improve code. |

## Where the project stands

The current **v0.1.0a1 engineering prerelease** provides an age-structured U.S. health-model foundation, verified mortality/life-table calculations, an evidence registry, scenario plumbing, and uncertainty tools. Important metabolic and dietary parameters remain synthetic. The scientific v0.1 release is unfinished.

Food-market feedback, GLP-1 adoption, a distinct PreChronic cohort, provider economics, real-option valuation, and the interactive Demeter Simulator are future work. Current outputs cannot support substantive dietary, market, or investment findings. Read the [detailed status](Evidence-and-Model-Status.md) before interpreting a run.

## Open by design

The [GitHub repository](https://github.com/Crusonia/Demeter) holds the code, evidence metadata, scenarios, and review history. The [MIT License](https://github.com/Crusonia/Demeter/blob/main/LICENSE) permits reuse under its terms. Individual external datasets retain their own terms.

The Substack supplies questions and discussion; evidence and reproducible analysis determine what the model can support. Our aim is a shared research tool that researchers, builders, operators, and policymakers can inspect and improve.
