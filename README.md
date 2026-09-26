# Demeter

**Demeter is a systems model of food, health, agriculture, and longevity.**

The project is intended to make the Food is Health thesis computable: explicit causal relationships, auditable evidence, quantified uncertainty, reproducible scenarios, and traceable downstream effects across population health, agriculture, economics, and policy.

## Project vision

The program vision and phased roadmap are documented in [docs/PROJECT_VISION.md](docs/PROJECT_VISION.md). The mature module/runtime architecture is in [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md), the long-term scenario surface is preserved in [docs/SCENARIO_CATALOG.md](docs/SCENARIO_CATALOG.md), and the recommended work after v0.1 is sequenced in [docs/POST_V0_1_ROADMAP.md](docs/POST_V0_1_ROADMAP.md). Historical validation requirements are defined in [docs/BACKTESTING_STRATEGY.md](docs/BACKTESTING_STRATEGY.md).

Demeter is designed as a hybrid system: system dynamics for aggregate stocks/flows and feedback loops, with agent-based modeling added selectively where heterogeneous behavior matters. Canonical naming is **Demeter** for the project/model, **Demeter Model** for the scientific model, and **Demeter Simulator** for the eventual interactive application. The scientific model remains locally reproducible; Codex Cloud is used for bounded autonomous engineering; Vercel is reserved for a later interactive interface rather than the core model runtime.

## North-star questions

Demeter is ultimately intended to identify **system leverage**: which upstream changes materially alter downstream health and economic outcomes, through what pathways, with what delays, feedbacks, and uncertainty.

Examples include:

- How does consumer price elasticity for higher-quality food affect dietary behavior and type 2 diabetes incidence?
- How do commodity-crop economics and processing scale create cheap calories relative to nutrient-dense food?
- How does nutrient density affect taste, satiety, food choice, and metabolic outcomes?
- Which links between agricultural practice, soil health, food composition, and chronic disease are strongly evidenced versus merely hypothesized?
- Under what conditions could regenerative or other production practices materially reduce chronic-disease burden?
- Which intervention points have the largest downstream impact per dollar, per acre, or per unit of behavioral change?
- Where do delays, reinforcing loops, balancing loops, and bottlenecks dominate the system?

These are research questions, not assumptions. Demeter should make the intermediate causal links explicit and allow the evidence and sensitivity analysis to determine which levers are material.

## Initial scope

Version 0.1 deliberately starts narrow:

```text
dietary exposure
      ↓
metabolic health
      ↓
chronic-disease incidence
      ↓
mortality
      ↓
life expectancy / healthy life expectancy
```

Agriculture, food-industry behavior, healthcare economics, policy, and agent-based adoption dynamics come after the health vertical slice is validated.

## Scientific rule

No substantive numerical claim belongs in Demeter unless its parameter is traceable to evidence and its uncertainty is represented. Placeholder values used for software development must be labeled `synthetic` and must never be presented as findings.

## Status

Phase 0 foundation is established. Phase 1 focuses on the evidence-backed health → longevity vertical slice. See [docs/PROJECT_VISION.md](docs/PROJECT_VISION.md) for the full roadmap through agriculture, agent behavior, healthcare economics/policy feedback, integrated modeling, and a later decision-support simulator.
