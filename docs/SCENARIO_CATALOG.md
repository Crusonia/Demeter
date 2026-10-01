# Demeter — Scenario Catalog

## Purpose

This document preserves the main scenario families Demeter should eventually support. It is not a commitment to implement all of them immediately.

Scenarios should be explicit interventions or condition sets, not ad hoc spreadsheet toggles.

## Scenario design rules

Each scenario should declare:

- what changes
- what is held constant
- time horizon and adoption path
- target geography/population
- relevant phase/module
- evidence-backed parameters versus scenario assumptions
- uncertainty and structural limitations

Future scenario design briefs should also cite relevant IDs from the
[loop, externality, and input registers](design/README.md), identify which loops
are closed versus cut by exogenous assumptions, and name the actor whose value
is being measured. Put this design context in companion Markdown/PRs; do not
add unsupported fields to the current strict scenario YAML schema.

## Phase 1 — health / longevity scenarios

### Baseline
- current/reference U.S. baseline

### Ultra-processed food
- lower UPF share
- UPF reformulation
- increased UPF share as counterfactual/stress scenario

### Nutrition exposure
- higher fiber intake
- increased fruit/vegetable intake
- improved protein quality
- reduced added sugar
- lower refined-carbohydrate load
- nutrient-density improvement when represented explicitly

### Clinical / preventive
- food-as-medicine uptake
- targeted intervention in prediabetes
- insurer/employer nutrition intervention

## Agriculture and food-system scenarios

### Production
- increased fruit/vegetable acreage
- regenerative acreage expansion
- conventional/regenerative share change
- crop switching
- yield shifts
- soil-health improvement
- livestock shifts where material

### Commodity and processing
- commodity-price shocks
- cheap-calorie intensification
- processing-capacity bottlenecks
- processing-capacity expansion
- food-manufacturer reformulation
- distribution / cold-chain improvements

### Food quality
- nutrient-density improvement
- product-composition improvement
- reduced residue / contaminant scenarios only where evidence justifies them

## Economics and behavioral scenarios

### Price and affordability
- relative price reduction for higher-quality food
- targeted nutrient-dense-food subsidy
- selected food-category tax/cost increases
- household food-budget changes

### Elasticity and substitution
- alternative own-price elasticity assumptions
- cross-price substitution between food groups
- household/income segmentation
- convenience or availability constraints interacting with price

### Consumer preference
- taste / satiety hypotheses
- habit persistence
- slow dietary adaptation
- adoption curves for dietary change

## Healthcare and policy scenarios

### Payer / healthcare
- Medicare or insurer food-intervention reimbursement
- employer-funded prevention
- targeted diabetes/prediabetes prevention
- prevention-versus-treatment spending shifts

### Agriculture / food policy
- subsidy redesign
- nutrient-density incentives
- regenerative-practice incentives
- procurement standards
- nutrition-benefit design

## Integrated north-star scenarios

### Flagship: shift toward real food across the value chain

How does a specified change in food baskets, access, and sustained consumption
affect agriculture, processing, distribution, retail, health, and healthcare
spending? Give each participant a lever and an account of added costs, benefits,
and captured value. Trace a specified regenerative practice through product
attributes, buyer response, and retail economics back to producer returns.

Within this scenario family, evaluate whether targeting a defined PreChronic
population changes disease progression and net healthcare costs relative to
a stated counterfactual. Include identification, intervention costs, persistence,
delays, and the allocation of savings. The distinct cohort and cost layer are
future work; the current UPF example is not a complete real-food scenario.

See [the flagship brief](REAL_FOOD_VALUE_CHAIN.md) for definitions, actor views,
and the staged learning exercise. This is a research agenda, not an implemented
economic model or a claim that the proposed changes produce a benefit.

### Relative food-price transition
How does a sustained reduction in the relative price of higher-quality food change dietary exposures, type 2 diabetes burden, healthcare cost, and agricultural supply response?

### Cheap-calorie system stress test
How much disease burden is plausibly attributable to a system that structurally makes calorie-dense, low-nutrient food cheaper than higher-quality alternatives?

### Nutrient-density pathway
Under what assumptions does increased nutrient density materially affect taste, satiety, food choice, and downstream metabolic outcomes?

### Production-practice pathway
Under what evidence-backed assumptions can production practices alter food composition enough to change chronic-disease burden?

### Food is Health policy bundle
What happens when reimbursement, food pricing, agricultural incentives, food formulation, and adoption behavior change together?

### Land competition, productivity and changing food demand

Compare solar/wind, data-center and urban-development siting/footprints with
retained agriculture and co-use. Test product-specific productivity and loss
changes, GLP-1 uptake/persistence and category substitution, and contracts versus
ownership integration under equivalent nutrient specifications, then separately
test nutrient-focused product/recipe mixes with adequacy and budget constraints.
Show regional
food/nutrient capacity and farm/tenant/community outcomes alongside national
totals. Family ownership and commercial scale are separate dimensions.

These are future learning exercises, not runnable scenarios or an optimizer.
The [land-use design brief](design/07_LAND_USE_AND_NUTRITION_TRADES.md) records
Q-05/RM-06, L-16/L-17/P-06/P-07, I-13 and F-09/T-09, sources and unresolved inputs.
The v0.1 health gate still precedes agricultural and market implementation.

## Implementation maturity path

1. **Single-module scenarios** — health exposure variables only.
2. **Linked-module scenarios** — price/quality/agriculture variables feed nutrition exposures.
3. **Integrated scenarios** — agriculture, economics, behavior, health, and policy interact simultaneously.

Future scenario files may evolve toward:

```text
scenarios/
  health/
  agriculture/
  economics/
  policy/
  integrated/
```
