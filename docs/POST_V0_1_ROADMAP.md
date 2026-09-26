# Demeter — Post-v0.1 Roadmap

## Purpose

This document defines the recommended implementation sequence after Issue #1 is complete.

The objective is to move from a validated health engine toward a true system-leverage model without jumping prematurely into the entire food/agriculture system.

---

## Step 0 — Historical reconstruction and backtesting harness

Before major upstream levers are added, Demeter should prove that its causal structure can reproduce historical dynamics it was not calibrated on.

The goal is not merely to fit today's cross-section. Demeter should reconstruct multiple recent decades of U.S. history and predict held-out periods.

### Historical data families

Candidate authoritative sources include:

- NCHS life tables and mortality data
- NHANES / historical NHES for metabolic, anthropometric, and nutritional state
- NHIS / CDC diabetes surveillance for diagnosed diabetes incidence and prevalence
- USDA ERS food-availability and loss-adjusted food-availability series
- USDA historical nutrient-availability series
- Census population estimates
- CMS / provider datasets when healthcare utilization and revenue modules are added

Use source vintages and definitions explicitly. Do not splice incompatible definitions without a documented transformation.

### Backtest design

Use at least two complementary designs.

#### Rolling-origin backtest

Example structure:

```text
calibrate through year T
        ↓
forecast T+5 / T+10
        ↓
compare with observed outcomes
        ↓
move T forward and repeat
```

This tests whether the model can reproduce changing trajectories rather than one endpoint.

#### Era holdouts

Potential eras, subject to data comparability:

- 1970s / early 1980s
- late 1980s / 1990s
- 2000s
- 2010s
- post-2020 as a separate structural-break regime rather than an ordinary validation period

Calibration and holdout targets must be kept separate.

### Backtest outputs

At minimum compare predicted versus observed:

- age-specific mortality
- life expectancy
- metabolic-state / diabetes prevalence
- diabetes incidence where comparable data exist
- selected anthropometric/metabolic risk distributions
- selected food-availability / dietary-exposure proxies
- later, chronic-disease utilization and provider economics

### Error metrics and diagnostics

Use:

- absolute and relative error
- cohort-specific residuals
- time-series residuals
- calibration versus holdout error
- structural-break diagnostics
- parameter drift
- sensitivity drift
- uncertainty coverage: how often observed values fall inside predicted intervals

### Historical shocks and confounders

The backtesting framework must allow material exogenous changes to be represented rather than forcing the food model to explain everything.

Candidate examples include:

- smoking decline
- hypertension treatment
- statin adoption
- diagnostic-definition changes
- demographic aging
- major medication classes
- recession / food-price shocks
- COVID-era mortality disruption
- GLP-1 adoption in recent periods

The purpose is to test causal structure, not to falsely attribute every historical health change to food.

### Release gate

No major integrated upstream module should be considered trustworthy until Demeter can:

1. reproduce its calibration period
2. predict at least one held-out historical period
3. explain material misses
4. show uncertainty coverage
5. preserve parameter and evidence provenance across vintages

---

## Step 1 — Model observability and visualization

Visualization is scientific instrumentation, not merely a future product feature.

Demeter should support reproducible views for:

- stock-and-flow structure
- causal-loop graphs
- state-transition diagrams
- historical observed-versus-predicted trajectories
- cohort trajectories over time
- scenario comparisons
- mortality and life-table curves
- uncertainty bands
- sensitivity rankings
- parameter distributions
- evidence-strength overlays on causal links
- contribution / attribution views
- residual/backtest diagnostics

Preferred open-source tooling:

- Plotly for interactive scientific charts
- NetworkX + Graphviz for causal/dependency graphs
- Marimo or Jupyter for exploratory analysis
- later, Cytoscape.js or an equivalent browser graph library for Demeter Simulator if useful

Visualization code must consume canonical model outputs rather than becoming a second model implementation.

---

## Step 2 — Make PreChronic a first-class cohort

Demeter should explicitly represent the **PreChronic** population: people not yet diagnosed with chronic metabolic disease and potentially still below formal prediabetes thresholds, but already showing underlying metabolic risk.

Potential signals may include, where evidence supports them:

- insulin resistance / hyperinsulinemia
- excess or visceral adiposity
- deteriorating glycemic control below formal diabetes thresholds
- elevated blood pressure
- adverse lipid patterns
- low cardiorespiratory fitness
- other early metabolic dysfunction

The concept should remain broader than a single laboratory cutoff.

A coarse first structure may be:

```text
metabolically healthy
        ↓
PreChronic
        ↓
prediabetes
        ↓
type 2 diabetes / chronic disease
```

with reversible transitions where evidence supports them.

Important outputs:

- size of the PreChronic cohort
- age distribution
- annual inflow into PreChronic
- annual reversal toward lower risk
- annual progression into prediabetes / diagnosed disease
- average time spent in PreChronic
- intervention reach and response
- contribution of PreChronic progression to future chronic-disease burden

Do not define PreChronic solely by A1c. A laboratory threshold can be an operational definition for a specific analysis, but the modeled concept is intended to capture the earlier risk state that conventional disease labels often miss.

---

## Step 3 — GLP-1 intervention and adoption dynamics

GLP-1 therapies should be modeled as a major intervention/exogenous shock affecting both health dynamics and, later, food demand.

Candidate health pathway:

```text
eligibility / access / price / coverage
        ↓
GLP-1 initiation
        ↓
persistence / discontinuation
        ↓
appetite / intake / weight / metabolic state
        ↓
PreChronic / prediabetes / diabetes transitions
        ↓
disease burden and mortality
```

Longer-term food-system pathway:

```text
GLP-1 adoption
        ↓
food quantity and category demand
        ↓
retail / food-company response
        ↓
agricultural demand and production mix
```

The model should distinguish:

- eligibility
- initiation
- persistence
- discontinuation
- re-initiation where evidence supports it
- access / insurance constraints
- price
- supply constraints when material
- heterogeneous treatment response
- post-discontinuation dynamics

Effects must be evidence-linked. Demeter should not assume permanent or universal effects.

---

## Step 4 — Chronic-disease utilization and provider economics

Demeter should translate changes in chronic disease into healthcare utilization, payer spending, and provider economics.

This is important because social savings and incumbent provider revenue can move in opposite directions.

Core pathway:

```text
PreChronic / chronic-disease burden
        ↓
ED visits / admissions / procedures / outpatient management
        ↓
payer spending
        ↓
hospital and health-system revenue
        ↓
capacity / fixed-cost pressure / service-line response
```

The model should distinguish:

- utilization
- allowed spending
- provider revenue
- contribution margin
- fixed versus variable cost
- payer mix
- service-line mix
- capacity reallocation
- prevention / ambulatory revenue substitution
- lag between disease reduction and financial response

A reduction in chronic disease should **not** be assumed to map one-for-one into hospital revenue decline.

Relevant questions include:

- Which hospital service lines are most exposed to lower chronic-disease incidence?
- How much revenue is delayed rather than permanently removed?
- How much cost can providers actually remove?
- Does capacity migrate to other procedures or conditions?
- Which provider types benefit from prevention while acute-care facilities lose volume?
- How do fee-for-service and value-based reimbursement change the direction of incentives?

---

## Step 5 — Consumer price, substitution, and diet

Build the first major upstream lever:

```text
relative food prices
        ↓
consumer demand / substitution
        ↓
food basket composition
        ↓
nutrition exposures
        ↓
PreChronic and chronic-disease transitions
```

Initial capabilities should include:

- own-price elasticity
- cross-price elasticity
- household budget / income effects
- household segmentation where evidence supports it
- lag / habit persistence
- separate price, convenience, and availability effects

---

## Step 6 — Commodity and processing economics

Explain why calories and food categories have the relative prices they do.

```text
commodity economics
+ crop yields
+ processing efficiency
+ ingredient economics
+ infrastructure
+ agricultural incentives
        ↓
retail relative food prices
        ↓
consumer behavior
        ↓
health
```

---

## Step 7 — Nutrient density, taste, satiety, and food choice

Test the harder quality pathway:

```text
food composition / nutrient density
        ↓
taste / satiety / preference
        ↓
quantity and category choice
        ↓
metabolic exposure
        ↓
health
```

Each intermediate link must be evidence-gated.

---

## Step 8 — Agriculture and production practices

Only after the downstream interfaces are stable should Demeter build the larger agricultural SD model.

```text
demand
 ↓
prices / margins
 ↓
acreage allocation
 ↓
production practices
 ↓
yield / costs / soil / composition
 ↓
food supply, price, quality
 ↓
consumer behavior
 ↓
health
 ↺
```

Regenerative and other production practices should enter as multiple testable pathways rather than as assumed health interventions.

---

## Step 9 — Integrated economic and policy feedback

Close the loops between:

- health outcomes
- healthcare spending
- provider economics
- payer incentives
- food demand
- agricultural economics
- policy
- capital allocation

At this point Demeter becomes the integrated system-leverage model described in the project vision.
