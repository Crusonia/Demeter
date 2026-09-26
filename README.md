# Demeter

**Demeter is a systems model of food, health, agriculture, and longevity.**

The project is intended to make the Food is Health thesis computable: explicit causal relationships, auditable evidence, quantified uncertainty, reproducible scenarios, and traceable downstream effects across population health, agriculture, economics, and policy.

## Project vision

The full program architecture, open-source tool choices, development/compute model, and phased roadmap are documented in [docs/PROJECT_VISION.md](docs/PROJECT_VISION.md).

Demeter is designed as a hybrid system: system dynamics for aggregate stocks/flows and feedback loops, with agent-based modeling added selectively where heterogeneous behavior matters. The scientific model remains locally reproducible; Codex Cloud is used for bounded autonomous engineering; Vercel is reserved for a later interactive interface rather than the core model runtime.

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
