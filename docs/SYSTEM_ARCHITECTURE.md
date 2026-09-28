# Demeter — System Architecture

## Purpose

This document preserves the intended mature architecture of Demeter so that narrow phase objectives do not accidentally redefine the program.

Demeter is intended to evolve from a narrow health model into a modular system spanning food, health, agriculture, economics, behavior, and policy.

Related documents:

- `docs/PROJECT_VISION.md` — program rationale, tooling, and phased roadmap
- `docs/SCENARIO_CATALOG.md` — scenario families
- `docs/CODEX_V0_1_OBJECTIVE.md` — current Phase 1 implementation objective
- `AGENTS.md` — scientific and engineering rules
- [Design inputs](design/README.md) — mechanism registers and contracts used before adding equations

## From design premise to module

The [causal-loop register](design/02_CAUSAL_LOOPS.md),
[externalities register](design/03_EXTERNALITIES.md), and
[input inventory](design/04_MODEL_INPUTS.md) feed the mature module design.
Select a decision and boundary, then trace its loop/pathway and input IDs into
explicit stock/flow equations, actor accounts, evidence keys, and the
[required validation experiments](design/05_FORMULATION_AND_TESTS.md).
Use the registers to expose missing mechanisms; do not build every proposed loop
or treat every listed quantity as an independent scenario input.

These Markdown files are review artifacts, not a new runtime loader. Their
premises do not activate states, parameters, modules, or clinical/commercial claims.

## Canonical product naming

Use these names consistently:

- **Demeter** — the overall project and underlying model/engine
- **Demeter Model** — the scientific/technical model
- **Demeter Simulator** — the eventual interactive decision-support application

The intellectual core is the model, evidence registry, equations, uncertainty structure, validation history, and scenario machinery. The UI is an interface to that asset.

## Canonical system decomposition

```text
Agriculture
    ↓
Food Supply / Processing
    ↓
Diet / Nutrition
    ↓
Health / Disease
    ↓
Longevity
    ↓
Healthcare Spending / Incentives
    ↓
Policy / Markets / Economics
    ↺ back to Agriculture and Food Supply
```

### Population and demographics

Responsibilities:

- age cohorts
- sex strata where justified
- mortality schedules
- life-table mechanics
- births / migration if future questions require them

Outputs include population by cohort, mortality, life expectancy, and healthy life expectancy.

### Health and disease

Responsibilities:

- metabolic-state transitions
- chronic-disease incidence
- disease-specific and all-cause mortality effects

Initial states:

- metabolically healthy / normoglycemic
- insulin resistant / prediabetes
- type 2 diabetes

Later candidate states include obesity/adiposity, cardiovascular disease, chronic kidney disease, selected cancers, and other material chronic disease categories.

### Nutrition and food exposure

Responsibilities:

- translate food consumption into biologically relevant exposures
- connect the food environment to health-state transitions

Candidate exposures include calories, protein quality, fiber, fruit/vegetable intake, micronutrients, added sugar, refined-carbohydrate load, ultra-processed-food share, omega-3/fat quality, and selected contaminants where evidence supports them.

### Food supply and processing

Responsibilities:

- bridge agriculture and consumer exposure
- represent processing, formulation, distribution, ingredient availability, retail/food-service channels, and product composition

Outputs include food prices, food availability, formulation mix, and exposure mix.

### Agriculture

Responsibilities:

- acreage allocation
- production mix
- crop switching
- livestock where material
- soil state
- regenerative/conventional transitions
- farm capital and economics
- processing/supply constraints

Candidate stocks include major acreage classes, fruit/vegetable acreage, pasture, regenerative acres, conventional acres, soil organic carbon, soil fertility, farm capital, and livestock inventories.

### Economics and policy

Responsibilities:

- food prices and affordability
- farm margins
- household food budgets
- healthcare expenditure
- payer/employer incentives
- subsidy and reimbursement structures

This layer closes the loop between health outcomes and the incentives that shape food production and consumption.

The intended reporting contract is an actor-by-actor view of incremental value
under a common scenario and counterfactual. Follow prices, volumes, costs,
margins, and payment terms across the chain so a participant can distinguish
value created elsewhere from the share it can capture. Keep transfers between
actors separate from additional system value and report timing and uncertainty.

For the [real-food flagship scenario](REAL_FOOD_VALUE_CHAIN.md), this includes
tracing regenerative production features to retail outcomes and back to producer
returns, and linking an evidence-supported PreChronic intervention to utilization,
intervention cost, and net spending by payer. An optional
[PreChronic state experiment](PRECHRONIC.md) now provides candidate definitions
and validation-only mechanics. Its clinical interpretation and calibration remain
unresolved. Healthcare-cost mechanics and an evidence-supported intervention
remain later work; no payer effect is implicit in the current health model.

### Behavioral / adoption layer

Use agent-based modeling selectively where heterogeneity matters materially.

Likely agent types:

- households / consumers
- farmers
- food companies
- insurers / payers

Mesa is the preferred open-source ABM framework unless a later evaluation identifies a better fit.

## Mature repository/module architecture

The codebase should be able to evolve toward:

```text
Demeter/
  AGENTS.md
  README.md
  pyproject.toml

  docs/
    PROJECT_VISION.md
    SYSTEM_ARCHITECTURE.md
    SCENARIO_CATALOG.md
    MODEL_SPEC.md
    phase_objectives/

  evidence/
    parameters/
    relationships/
    sources/
    manifests/

  data/
    raw/
    processed/
    manifests/

  scenarios/
    health/
    agriculture/
    economics/
    policy/
    integrated/

  src/demeter/
    population/
    health/
    nutrition/
    food_system/
    agriculture/
    economics/
    policy/
    agents/
    evidence/
    data/
    scenarios/
    calibration/
    analysis/
    cli/

  tests/
    unit/
    integration/
    validation/
```

Early phases may implement only a subset.

### Module intent

- `population/` — cohorts, mortality baselines, life tables, demographic mechanics
- `health/` — state transitions, disease models, risk modification
- `nutrition/` — dietary exposures and mapping from food basket to biological exposure
- `food_system/` — processing, formulation, product mix, retail food environment
- `agriculture/` — acreage, production, soil, livestock, supply response
- `economics/` — prices, elasticities, healthcare costs, budget constraints
- `policy/` — subsidies, incentives, reimbursement scenarios, regulatory levers
- `agents/` — heterogeneous actors where aggregate equations are insufficient
- `evidence/` — typed parameter registry, provenance, evidence grades
- `data/` — reproducible fetch/transforms and data manifests
- `calibration/` — statistical estimation and calibration, likely using PyMC later
- `analysis/` — uncertainty propagation, sensitivity analysis, attribution, reporting
- `scenarios/` — typed scenario definitions and validation
- `cli/` — command-line scientific execution surface

## Price, quality, and consumer behavior

One of Demeter's central goals is to understand how economic structure affects food choice and health.

The intended causal path is:

```text
commodity economics / agricultural incentives / processing scale
        ↓
relative price of food categories
        ↓
household affordability and substitution behavior
        ↓
food basket composition
        ↓
nutrient / exposure profile
        ↓
metabolic-state transitions
        ↓
type 2 diabetes and chronic-disease burden
```

Future models should be capable of representing:

- own-price elasticity
- cross-price elasticity and food substitution
- income effects and household budget constraints
- segmentation by household type where evidence supports it
- quality-adjusted food demand
- convenience and availability constraints
- interaction between price, taste, satiety, and habit
- feedback from demand changes into production economics

Price should not be modeled as an isolated scalar. The important question is how relative prices change behavior and how those behavioral changes translate into biological exposure.

## Runtime and compute architecture

### Canonical scientific runtime

The scientific model must remain reproducible from a fresh local clone.

```bash
uv sync
uv run demeter validate
uv run demeter simulate scenarios/...
```

The core model must not require Vercel, a browser, or a hosted proprietary runtime.

### Codex Desktop / local workstation

Best for:

- architecture
- equations
- data exploration
- notebooks and plots
- debugging
- scientific diagnosis

### Codex Cloud

Best for:

- bounded autonomous engineering
- implementation against repository-native objectives
- tests and refactors
- data pipelines
- large repository tasks

Cloud is an engineering extension, not the canonical scientific runtime.

### Batch compute

Introduce dedicated batch compute only when required for:

- Monte Carlo
- Bayesian calibration
- Sobol sensitivity analysis
- large parameter sweeps
- larger ABM experiments

### Vercel and Demeter Simulator

Vercel is intended for the eventual **Demeter Simulator** interface, not the scientific engine.

Likely separation:

```text
full Demeter Model / local or batch compute
                ↓
        results / scenario outputs
                ↓
        Demeter Simulator on Vercel
```

### Surrogate / emulator layer

If the full model is too expensive for real-time slider interaction:

```text
full model parameter space
        ↓
many trusted model runs
        ↓
scenario/output dataset
        ↓
surrogate / emulator
        ↓
instant interactive UI
```

The full Demeter Model remains the source of truth.

## Architecture principles

1. Model the causal path, not only the headline result.
2. Keep evidence, equations, and scenario assumptions separate.
3. Let phase objectives narrow implementation without redefining the long-term system.
4. Preserve modular boundaries even in early phases.
5. Use the simplest representation that preserves causal fidelity.
6. Introduce ABM only when heterogeneity materially matters.
7. Avoid UI-led scientific architecture.
8. Treat uncertainty and validation as product requirements.
9. Preserve future interfaces for agriculture, economics, behavior, and policy.
10. Never encode a desired Food is Health conclusion as a model assumption.
