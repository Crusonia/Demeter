# Demeter — Project Vision, Architecture, Tooling, and Roadmap

## Companion architecture documents

This document defines the program vision and roadmap. Use these companion documents for more specific long-term design intent:

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) — canonical mature module/runtime architecture, product naming, and price/quality behavioral mechanism
- [SCENARIO_CATALOG.md](SCENARIO_CATALOG.md) — scenario families and integrated north-star experiments
- [CODEX_V0_1_OBJECTIVE.md](CODEX_V0_1_OBJECTIVE.md) — current Phase 1 implementation objective

---

## 1. What Demeter is

Demeter is an open-source project under the [Food is Health Substack](https://foodishealth.substack.com/). Its public mission is to model the market dynamics linking food, agriculture, health, and capital: identify consequential levers, trace constraints and feedback, and examine how strategic options change as underlying trends move.

The [public guide](wiki/Home.md) explains that mission. [Real options and strategic value](wiki/Real-Options-and-Strategic-Value.md) describes a future decision-analysis layer for piloting, waiting, scaling, switching, and exiting under uncertainty. This layer must remain downstream of the evidence-backed scientific model. Documenting it does not expand the current v0.1 implementation boundary or authorize investment conclusions from synthetic outputs.

Demeter is intended to become a **computable version of the Food is Health thesis**.

The long-term question is not simply:

> Does better food improve health?

The system question is:

> If the food system changes, how do the effects propagate through diet, metabolic health, chronic disease, lifespan, healthcare spending, agricultural production, land use, farm economics, food-company behavior, insurance incentives, and public policy — and what feedback loops then reshape the food system again?

Demeter should make those causal paths explicit, testable, evidence-linked, uncertainty-aware, and reproducible.

The long-term system is approximately:

```text
                       ┌──────────────────────┐
                       │   Policy / Markets   │
                       └──────────┬───────────┘
                                  │
                                  ▼
┌─────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
│ Agriculture │ ────► │ Food supply / price  │ ────► │ Diet / nutrition     │
└──────┬──────┘       │ / nutrient quality   │       │ exposures            │
       ▲              └──────────────────────┘       └──────────┬───────────┘
       │                                                        │
       │                                                        ▼
       │                                            ┌──────────────────────┐
       │                                            │ Metabolic health     │
       │                                            └──────────┬───────────┘
       │                                                       │
       │                                                       ▼
       │                                            ┌──────────────────────┐
       │                                            │ Chronic disease      │
       │                                            └──────────┬───────────┘
       │                                                       │
       │                                                       ▼
       │                                            ┌──────────────────────┐
       │                                            │ Mortality / healthy  │
       │                                            │ lifespan             │
       │                                            └──────────┬───────────┘
       │                                                       │
       │                                                       ▼
       │                                            ┌──────────────────────┐
       └────────────────────────────────────────────│ Healthcare spending  │
                                                    │ / economic response  │
                                                    └──────────────────────┘
```

The model should eventually support second-, third-, and fourth-order consequences rather than isolated point estimates.

---

## 2. Core modeling philosophy

Demeter should be a **hybrid model**, not one giant system-dynamics diagram.

Different parts of the system require different mathematical representations.

### System dynamics is the backbone

Use system dynamics for aggregate stocks, flows, delays, and feedback loops such as:

- population cohorts
- metabolic-health states
- chronic-disease prevalence
- agricultural acreage
- soil state
- processing capacity
- healthcare spending
- farm capital
- food demand
- policy and market feedbacks

### Agent-based modeling is selective

Use agents only where heterogeneity and local decision rules materially affect the result.

Likely agents later include:

- farmers
- households / consumers
- food companies
- insurers / payers
- healthcare systems

Examples of questions that belong in an agent model:

- When does a farmer adopt a new practice?
- How do neighboring farms affect adoption?
- How does price sensitivity differ by household?
- When does a food company reformulate a product?
- When does an insurer fund a food-as-medicine intervention?

Do **not** model everything as agents merely because agents are available.

### Multiple time scales are unavoidable

Demeter spans:

- weeks/months — biomarkers and dietary change
- years — metabolic disease incidence and remission
- decades — mortality and lifespan
- years/decades — farm equipment, acreage, soil, and processing-capacity turnover
- election/budget cycles — policy response
- investment cycles — food and agricultural capital formation

The architecture must make these time scales explicit rather than implicitly forcing everything onto one clock.

---


## North-star leverage questions

Demeter exists to understand **system leverage, feedback, delays, and unintended consequences** across food, health, agriculture, and economics. The model should eventually be able to test questions such as:

- How does the price elasticity of demand for higher-quality food change dietary behavior, metabolic disease incidence, and long-run healthcare burden?
- At what relative price does healthier food become behaviorally competitive with cheap calorie-dense food for different household segments?
- How do commodity-crop economics, subsidies, processing infrastructure, and scale economies lower the price of calories relative to nutrient-dense foods?
- How does nutrient density affect taste, satiety, food preference, consumption, and downstream metabolic outcomes?
- Which parts of the relationship between soil health, farming practice, crop nutrient density, food quality, and human health are strongly evidenced, weakly evidenced, or merely hypothesized?
- Under what conditions could regenerative or other production practices materially change chronic-disease burden through nutrient quality, food composition, chemical exposure, price, availability, or other pathways?
- Which intervention points produce the largest downstream health benefit per dollar, per acre, or per unit of behavioral change?
- Where are the dominant delays, bottlenecks, reinforcing loops, and balancing loops that make food-system change slow or nonlinear?
- Which apparent levers matter little once the whole system is modeled, and which second-order effects dominate outcomes?
- What fraction of chronic-disease burden is plausibly addressable through food-system change, through which causal pathways, and with what uncertainty?

These are **research questions, not encoded conclusions**. Demeter must represent the intermediate causal links explicitly and allow the evidence to determine whether a hypothesized pathway is material.

The implementation sequence should therefore distinguish between:

```text
NORTH STAR
understand leverage across the whole food-health system

        ↓ implemented in stages

PHASE 1
nutrition exposure → metabolic health → disease → mortality

PHASE 2+
prices / quality / agriculture / behavior → nutrition exposure

PHASE 3+
feedback from health economics / policy / markets → agriculture and food supply
```

The purpose of the phased roadmap is to make the eventual system-level conclusions more credible, not to narrow Demeter into a health-only model.

## 3. Primary model domains

### 3.1 Population and health

Core stocks may include:

```text
population by age / sex
metabolically healthy
insulin resistant / prediabetes
type 2 diabetes
cardiovascular disease
chronic kidney disease
selected cancers
other chronic disease
death
```

The first implementation should remain narrower than this full list.

The important architectural principle is that **life expectancy is an emergent output** from age-specific mortality schedules and health-state transitions. It should not be inserted as a direct assumed effect.

A simplified causal path:

```text
population at risk
      ↓
metabolic state
      ↓
disease incidence
      ↓
disease-specific / all-cause mortality
      ↓
life table
      ↓
life expectancy / healthy life expectancy
```

Backward health transitions should be supported when evidence justifies them.

---

### 3.2 Nutrition and dietary exposures

Demeter should avoid reducing food to a binary "good food / bad food" score.

Candidate modeled exposures include:

- calories
- protein quantity and quality
- fiber
- fruit / vegetable intake
- micronutrients
- omega-3 intake
- added sugar
- refined carbohydrate load
- ultra-processed-food share
- alcohol
- selected contaminants / toxins when evidence supports modeling them

Food exposure is influenced by:

- price
- availability
- income
- convenience
- culture
- clinical recommendations
- food benefits
- insurer incentives
- medications such as GLP-1 therapies
- product formulation

The nutrition layer should feed health transitions only through explicit, evidence-linked mechanisms.

---

### 3.3 Agriculture

Later phases should model agricultural supply response.

Candidate stocks:

```text
corn acres
soy acres
wheat acres
fruit / vegetable acres
pasture
regenerative acres
conventional acres
soil organic carbon
soil fertility
farm capital
processing capacity
livestock inventories
```

Candidate flows:

```text
crop switching
land conversion
regenerative-practice adoption
soil degradation
soil restoration
capital investment
farmer entry / exit
processing-capacity expansion
```

A core feedback loop:

```text
food demand
    ↓
commodity / product prices
    ↓
farmer margins
    ↓
acreage allocation
    ↓
production
    ↓
food availability / price
    ↓
food demand
```

A key long-term Demeter question is:

> What happens to U.S. agriculture if a material share of Americans begins optimizing food consumption around metabolic health rather than calories, convenience, or current dietary patterns?

---

### 3.4 Adoption and innovation

The adoption layer will likely combine system dynamics with Mesa-based agents.

Farmer decision rules may depend on:

- expected ROI
- capital requirements
- crop insurance
- transition risk
- financing
- neighbor adoption
- technical support
- commodity prices

Consumer decision rules may depend on:

- price
- income
- health status
- physician recommendation
- convenience
- social norms
- insurance / employer benefits

Food-company behavior may depend on:

- reformulation cost
- expected demand
- channel response
- regulatory constraints
- ingredient availability

The initial ABM does **not** require millions of agents. Representative archetypes are likely sufficient for many questions.

---

### 3.5 Economics, healthcare, and policy

Demeter should eventually close the loop between health outcomes and economic incentives.

A core feedback:

```text
chronic disease
      ↓
healthcare cost
      ↓
employer / Medicare / insurer spending
      ↓
economic incentive for prevention
      ↓
food-is-health intervention
      ↓
dietary exposure
      ↓
chronic disease
```

Candidate scenarios later include:

- medically tailored food reimbursement
- food benefits targeted to metabolic disease
- commodity-support redesign
- nutrient-density incentives
- regenerative-practice incentives
- reduced UPF consumption
- improved crop nutrient density
- insurer-funded prevention
- food-company reformulation

Demeter should simulate policies; it should not prescribe a policy conclusion automatically.

---

## 4. Open-source technical stack

Demeter should remain code-first and open-source-tool friendly.

### Core system dynamics — BPTK-Py

**Preferred role:** primary system-dynamics engine where it improves clarity.

Use for:

- stocks and flows
- delays
- feedback loops
- scenario execution
- multidimensional cohort models
- hybrid SD / ABM integration where useful

Why it fits:

- Python-native
- inspectable in a code repository
- compatible with Codex
- supports system dynamics and agents
- more automation-friendly than GUI-first SD tools

Do not force BPTK-Py into calculations that are simpler and more auditable in transparent NumPy code.

---

### Existing system-dynamics models — PySD

**Preferred role:** interoperability.

Use PySD when Demeter needs to:

- ingest existing Vensim models
- run or compare legacy system-dynamics models in Python
- reuse published SD work without manually rebuilding it

PySD is not necessarily the primary Demeter engine.

---

### Agent-based modeling — Mesa

**Preferred role:** heterogeneous actors and adoption dynamics.

Use later for:

- farmer decisions
- household decisions
- food-company behavior
- diffusion of innovation
- spatial or network effects

ABM should be introduced only where aggregate equations fail to represent material heterogeneity.

---

### Sensitivity analysis — SALib

**Preferred role:** global sensitivity analysis.

Use for:

- Sobol analysis
- Morris screening
- identifying which uncertain parameters dominate output variance

One of Demeter's most strategically useful outputs may be:

> Which variables dominate the outcome?

rather than a single headline forecast.

Examples:

```text
drivers of healthy life expectancy
drivers of T2D prevalence
drivers of agricultural transition
drivers of healthcare savings
drivers of farm income
```

---

### Bayesian calibration — PyMC

**Preferred role:** uncertain parameter estimation and calibration.

Use later for:

- calibrating transition rates
- estimating latent parameters
- combining evidence sources
- posterior uncertainty
- comparing competing parameterizations

PyMC should be added after basic model semantics and validation are stable.

---

### Survival and lifespan — transparent life tables + SciPy / lifelines

**Preferred role:** mortality and survival calculations.

Demeter should implement auditable life-table arithmetic directly.

SciPy and/or lifelines may support:

- survival functions
- hazard models
- validation calculations
- mortality analysis

Life expectancy should be calculated from mortality schedules, not inserted as an assumed outcome.

---

### Data engine — DuckDB + Polars + Parquet

**Preferred role:** local analytical data layer.

Use for:

- CDC / NCHS
- NHANES
- USDA
- Census
- CMS
- FAO
- agricultural datasets
- large scenario outputs

Design goal:

```text
raw immutable evidence
       ↓
reproducible transforms
       ↓
Parquet / typed model-ready data
       ↓
DuckDB / Polars analysis
       ↓
model parameterization
```

Avoid introducing a network database merely to solve local analytical problems.

---

### Causal and dependency graphs — NetworkX + Graphviz

**Preferred role:** make causal structure inspectable.

Use for:

- causal-link maps
- dependency graphs
- stock/flow dependency visualization
- evidence gaps
- model-module relationships

The graph should help reviewers see:

```text
assumption → equation → state transition → output
```

---

### Exploration — Marimo or Jupyter + Plotly

**Preferred role:** scientific exploration and diagnostics.

Use for:

- trajectory inspection
- calibration diagnostics
- scenario comparison
- sensitivity plots
- cohort inspection
- evidence exploration

Notebooks are exploration surfaces, not the canonical model.

The model must remain callable from Python and CLI without a notebook.

Marimo is attractive because it is more reproducible than traditional free-form notebook state, but Jupyter remains acceptable for exploratory work.

---

### Public simulator — SDEverywhere or custom React / Next.js

**Preferred role:** later public decision-support interface.

Two viable paths:

1. **SDEverywhere**
   - useful for an En-ROADS-like system-dynamics simulator
   - browser execution
   - WebAssembly / JavaScript compilation pathways

2. **Custom React / Next.js**
   - preferred if the public product needs a bespoke UX
   - scenario controls
   - charts
   - explanations
   - evidence drill-down

The UI is not the source of truth.

---

### Testing and engineering

Use:

- **pytest** — model and software tests
- **Ruff** — linting / formatting
- **uv** — Python environment and package management
- **GitHub Actions** — CI
- deterministic random seeds for stochastic tests

Testing should include scientific invariants, not merely software coverage.

Examples:

- population conservation
- dimensional consistency
- bounds
- life-table arithmetic
- scenario equivalence
- monotonicity where scientifically justified
- reproducibility
- evidence completeness

---

## 5. Evidence architecture

Demeter's real intellectual property is not the user interface.

It is:

```text
causal graph
+ equations
+ parameter definitions
+ evidence provenance
+ uncertainty distributions
+ validation history
+ scenario assumptions
```

Every material relationship should eventually have machine-readable metadata.

Example:

```yaml
parameter: diabetes_rr_from_exposure

value: ...
unit: relative_risk_per_defined_exposure_change

status: estimated

evidence:
  source: ...
  evidence_type: meta_analysis
  population: ...
  geography: ...
  period: ...

causal_confidence: B

uncertainty:
  distribution: ...
  low: ...
  high: ...

lag:
  years: ...

model_role:
  modifies: prediabetes_to_t2d_transition
```

Evidence strength should remain separate from effect size.

A useful working classification:

- **A** — strong causal evidence
- **B** — strong prospective / high-quality observational evidence
- **C** — observational or mechanistic evidence with substantial causal uncertainty
- **D** — expert / modeling assumption
- **E** — synthetic software-validation placeholder

Demeter should eventually be able to run scenarios such as:

> Use only A/B relationships.

or:

> Include C/D hypotheses and show how much they change the result.

That distinction is important to prevent the model from laundering hypotheses into apparent facts.

---

## 6. Development and compute architecture

### Canonical source — GitHub

GitHub is the canonical home for:

- code
- model definitions
- evidence metadata
- tests
- scenarios
- documentation
- release history

The repository should remain sufficient to reproduce the model.

---

### Codex Desktop / local workstation

**Primary use:** interactive model development and diagnosis.

Best for:

- model architecture
- equations
- data exploration
- notebooks
- plots
- debugging
- inspecting trajectories
- investigating unexpected model behavior
- large local datasets
- scientific iteration

The fundamental model must always be runnable locally.

Target pattern:

```bash
git clone ...
uv sync
uv run demeter validate
uv run demeter simulate scenarios/baseline.yaml
```

No Vercel, browser, or proprietary hosted runtime should be required to reproduce the scientific model.

---

### Codex Cloud

**Primary use:** bounded autonomous engineering and long-running repository work.

Best for:

- implementing well-specified modules
- refactoring
- adding tests
- building data pipelines
- large code changes
- executing acceptance criteria
- preparing PRs
- autonomous work against a clear objective

Codex Cloud should work from repository-native specifications such as:

- `AGENTS.md`
- phase objective documents
- tests
- issues
- acceptance criteria

Cloud is an engineering extension, not the canonical model runtime.

---

### Heavy batch compute

Do not introduce dedicated cloud compute until the model needs it.

Likely future workloads:

- Monte Carlo runs
- Sobol sensitivity analysis
- Bayesian calibration
- large parameter sweeps
- large ABM runs

At that point, use an appropriate batch-compute environment.

Keep compute orchestration separate from model semantics.

---

### Vercel

**Use Vercel for the interface, not the core scientific compute engine.**

Vercel is a good fit later for:

- Next.js UI
- scenario controls
- dashboards
- visualization
- authentication
- result retrieval
- lightweight API calls

Avoid making Vercel the only place the model can run.

A likely production architecture:

```text
                       GitHub
                         │
         ┌───────────────┴───────────────┐
         │                               │
   local / batch model              Vercel UI
         │                               │
         ▼                               ▼
  full simulations                scenario request
         │                               │
         └──────────► results ◄──────────┘
```

---

## 7. Fast public simulation via surrogate models

The full scientific model may eventually be too expensive to execute interactively for every slider movement.

Do **not** compromise the scientific model to make the web UI fast.

Instead:

```text
full parameter space
       ↓
many authoritative model runs
       ↓
scenario/result dataset
       ↓
surrogate / emulator / interpolation model
       ↓
fast web simulator
```

The full model remains the source of truth.

The surrogate is only an interaction accelerator.

This allows the public simulator to feel instantaneous while preserving a much richer underlying model.

---

## 8. Project phases

The phases below describe the intended program sequence. Version numbers are directional, not contracts.

### Phase 0 — foundation

**Goal:** create a trustworthy modeling substrate.

Deliverables:

- repository structure
- CLI
- evidence registry
- scenario schema
- test framework
- CI
- synthetic validation model
- scientific-output guardrails

Status: initiated.

---

### Phase 1 — health / longevity vertical slice

**Goal:** prove an evidence-backed end-to-end causal path.

Scope:

```text
dietary exposure
      ↓
metabolic state
      ↓
disease risk
      ↓
age-specific mortality
      ↓
life expectancy / healthy life expectancy
```

Key deliverables:

- U.S. age-structured population
- authoritative life-table baseline
- metabolic states
- selected dietary exposures
- evidence-linked transition effects
- uncertainty propagation
- historical validation
- sensitivity analysis
- reproducible CLI

This is the current v0.1 focus.

---

### Phase 2 — agriculture supply response

**Goal:** connect changes in food demand to agricultural production.

Add:

- acreage by major use
- crop switching
- livestock where material
- yields
- soil state
- farm economics
- input costs
- processing capacity
- selected nutrient-density variables
- regenerative / conventional transitions

Primary question:

> How does a health-driven demand shift alter what agriculture produces, where capital flows, and what food costs?

---

### Phase 3 — behavioral adoption / ABM

**Goal:** represent heterogeneous adoption and diffusion.

Add representative agents for:

- farmers
- households
- food companies

Potential later agents:

- insurers
- health systems
- retailers

Use Mesa selectively.

Primary questions:

- What slows adoption?
- What creates tipping points?
- Where do network effects matter?
- Which incentives change behavior fastest?

---

### Phase 4 — healthcare economics and policy feedback

**Goal:** close the economic loop.

Add:

- healthcare utilization / spending
- payer incentives
- employer incentives
- Medicare / Medicaid scenario mechanics where appropriate
- food-benefit programs
- selected agricultural policy levers
- capital-allocation response

Primary question:

> When health improves, who captures the economic benefit, and does that create enough incentive to change the food system?

---

### Phase 5 — integrated Food is Health system

**Goal:** integrate the major modules into one auditable system.

At this phase Demeter should connect:

```text
agriculture
↕
food supply / prices
↕
diet
↕
health
↕
longevity
↕
healthcare economics
↕
policy / market incentives
↕
agriculture
```

Requirements:

- stable interfaces between modules
- uncertainty carried across module boundaries
- sensitivity decomposition
- scenario attribution
- explicit structural uncertainty
- independent validation where possible

---

### Phase 6 — decision-support simulator

**Goal:** make Demeter useful interactively.

Potential controls:

```text
UPF consumption
fruit / vegetable intake
fiber
nutrient density
food-as-medicine adoption
regenerative acreage
selected subsidies / incentives
selected healthcare incentives
```

Potential outputs:

```text
life expectancy
healthy life expectancy
T2D prevalence
CVD burden
healthcare spending
food expenditure
farm income
crop acreage
commodity prices
soil metrics
federal / payer expenditure
```

The interface may be:

- internal first
- later public
- potentially analogous to En-ROADS in interaction style

The simulator must expose uncertainty and evidence quality rather than showing false precision.

---

### Phase 7 — ongoing model governance

**Goal:** make Demeter a living evidence system.

Add processes for:

- source updates
- parameter re-estimation
- data-vintage tracking
- model-version comparison
- evidence-quality review
- sensitivity drift
- validation drift
- reproducible releases

Eventually, when a new study or USDA / CDC dataset is incorporated, Demeter should make clear:

- what parameter changed
- why it changed
- which outputs moved
- how much confidence changed

---

## 9. What Demeter should optimize for

Priority order:

1. **scientific traceability**
2. **causal clarity**
3. **reproducibility**
4. **uncertainty honesty**
5. **modularity**
6. **testability**
7. **computational performance**
8. **UI convenience**

Do not reverse this order merely to create a compelling demo.

---

## 10. What Demeter should not become

Avoid:

- a giant causal spaghetti diagram
- an LLM-generated collection of unsupported causal claims
- a black-box machine-learning forecast
- a nutrition ideology encoded as equations
- a web dashboard with no reproducible model underneath
- a single deterministic "years of life gained" calculator
- a policy advocacy engine
- a system where assumptions are indistinguishable from evidence
- a model whose core behavior can only run in a hosted proprietary environment

---

## 11. Strategic outputs

Demeter should eventually answer questions in several different forms.

### Forecast / scenario output

Example:

> Under a specified dietary-adoption scenario, what changes occur in metabolic disease, mortality, healthcare spending, farm acreage, and farm income over 10, 20, and 30 years?

### Leverage output

Example:

> Which five parameters explain most of the variance in healthy life expectancy?

Use tornado diagrams to show the direction and magnitude of output changes across explicit input ranges, with a baseline, units, horizon, and evidence status. Pair them with causal-path inspection, global sensitivity, and interaction analysis. Decision-focused tornado diagrams should also reveal which assumptions change the advantage of acting, waiting, scaling, switching, or exiting. See the [visualization specification](wiki/Visualization-and-Tornado-Diagrams.md). These are planned diagnostics; a sensitivity ranking alone does not establish a causal effect or an actionable intervention.

### Constraint output

Example:

> What prevents agricultural supply from responding fast enough to a large shift in dietary demand?

### Evidence-gap output

Example:

> Which causal links dominate the result but have weak evidence?

### Investment / innovation map

Demeter may later inform investment research by revealing bottlenecks and leverage points, but investment scoring should remain downstream of the scientific model rather than embedded in model equations.

---

## 12. Long-term product concept

The long-term vision is a model that allows a user to change an assumption about nutrition, agriculture, healthcare, or policy and trace the consequences through the system.

Conceptually:

```text
change assumption
      ↓
trace causal path
      ↓
show stock / flow changes
      ↓
show uncertainty
      ↓
show evidence strength
      ↓
show second- and third-order consequences
      ↓
identify dominant constraints and leverage points
```

That is the core of Demeter.

The website, charts, and scenario sliders are only interfaces to that deeper asset.
