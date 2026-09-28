# Problem, behavior, and boundary

Status: design premises for the future integrated model. Start with the
[design index](README.md); preserve the existing v0.1 health gate.

## Decisions the model should improve

| ID | Decision and perspective | Result to explain |
| --- | --- | --- |
| Q-01 | A producer/supplier adds a specified regenerative practice or enabling feature. | Whether value reaches processing and retail, who captures it, and whether producer returns cover transition costs and risk. |
| Q-02 | A processor, distributor, retailer, or household supports a specified real-food basket. | How price, availability, substitution, persistence, and capacity affect adoption and margins across the chain. |
| Q-03 | A provider, payer, employer, or public program targets a defined PreChronic population. | Whether sustained intervention changes progression, net healthcare costs, and the incentive to keep funding prevention. |
| Q-04 | An actor finances a pilot, measurement system, contract, or capacity change. | Which uncertainty or bottleneck matters, who can act on the information, and whether a viable payment mechanism exists. |

The goal is to explain conditional behavior and locate consequential levers.
Do not begin by selecting a desired return, cost reduction, or optimal policy.

## Reference modes: behavior to explain before fitting parameters

A reference mode is an observed or explicitly hypothesized trajectory over time,
not a target number the model must reproduce. Assemble series with consistent
definitions, draw the patterns, and record competing explanations first.

| ID | Behavior question | Observations needed; currently unresolved for this purpose |
| --- | --- | --- |
| RM-01 | Does a regenerative/verified-product premium persist, disappear, or fail to reach farms? | Matched farm/wholesale/retail prices, volumes, verification costs, contract terms, and margins for a defined product. |
| RM-02 | Does real-food adoption grow, saturate, or reverse? | Defined household food baskets, purchases versus intake, repeated participation, prices, income, access, and substitution. |
| RM-03 | Do shortages, waste, or prices fluctuate as demand and capacity adjust? | Inventories, orders, spoilage, lead times, investment commitments, installed capacity, and utilization. |
| RM-04 | When do health and payer-cost effects appear after earlier-risk intervention? | Defined eligibility, enrollment/attrition, exposures, progression, utilization, net program cost, and payer membership over time. |
| RM-05 | Do environmental or knowledge spillovers change with adoption? | Baseline and counterfactual physical loads, exposed recipients, or knowledge reuse, including displacement elsewhere. |

No trajectory above has been established as Demeter's empirical reference mode.
The current mortality/population and historical bundles do not establish the
retail, PreChronic, or intervention-cost series. Allocate calibration and holdout
periods before estimating a relationship; preserve changes in definitions/vintages.

## Boundary table

Endogenous means calculated through model relationships. Exogenous means supplied
from outside a particular experiment. A lever is an actor's feasible action or
decision rule; it is not automatically an independent external input.

| Quantity/domain | Intended treatment in a linked experiment | Current boundary and consequence |
| --- | --- | --- |
| Age/state population and mortality | Endogenous cohort evolution from observed initial population and specified hazards. | Implemented mechanics; metabolic allocation/effects still synthetic. Births/migration are zero in the current closed-population model. |
| PreChronic eligibility and progression | Separately defined risk population and evidence-supported transitions, with overlap handled explicitly. | [Optional candidate definitions and four-state mechanics](../PRECHRONIC.md) are implemented for validation; clinical mapping/rates remain unresolved. The original IR proxy is not renamed PreChronic, and people are not counted twice. |
| Food purchases and intake | Endogenous responses to price, access, habit, and defined interventions. | Current exposure multipliers are exogenous software scenarios; demand/health feedback is severed. |
| Agriculture, soil, supply, and inventories | Endogenous within the selected product/geography where required by the question. | Later modules; weather and external commodity conditions may be scenario paths. Global land/market displacement must be bounded or reported as omitted. |
| Retail prices, premiums, and margins | Endogenous responses to costs, scarcity, demand, and contracts. | Future. Do not impose a demand path and its presumed price/premium response simultaneously. |
| Capacity, learning, and adoption | Accumulated states responding to expected returns and perceived signals, with bounded decisions and delays. | Future. Forecasts of these states are temporary boundary assumptions, not a closed loop. |
| Healthcare use and expenditure | Endogenous to defined disease/coverage states and payment arrangements. | Future. Health improvements currently have no modeled dollar conversion. |
| Funding and payment rules | Scenario choices or actor decision rules; actual payments follow realized eligible events/terms. | Future. Savings do not automatically refill a prevention budget. |
| Climate/water/biodiversity spillovers | Physical outputs or explicitly bounded external modules for the selected question. | Register candidate effects now; no full climate/ecosystem model in v0.1. |
| Household income, wages, macroeconomy | Supplied scenario paths initially; endogenize only a material mechanism with evidence. | Feedback from health to earnings is omitted unless specifically selected and validated. |

## Time, population, and aggregation

The current foundation is U.S. age/sex cohorts and annual health steps. A future
study must choose a product, region, earlier-risk definition, baseline year,
decision horizon, and relevant actor segments. Those choices remain unresolved
for the flagship exercise; do not invent one universal real-food basket.

Shopping, inventory, and working-capital cycles may need shorter steps than
disease progression, soil change, or capacity turnover. Select steps through
convergence and delay tests. Preserve quantities when exchanging faster and slower
modules. Do not silently use a monthly effect as an annual rate or hide retail
stockouts inside an annual average. Keep the core runtime locally reproducible.

Disaggregate when it can change the decision: household access/income, farm/product
conditions, payer retention, or channel bargaining. Report what aggregation loses.
Begin with transparent cohorts/segments; add agents only for a demonstrated
heterogeneity or interaction requirement.

## Minimum result for each participant

Show the common counterfactual; feasible action; time path of physical effects;
incremental revenue, costs, cash, and capital by actor; uncompensated spillovers;
uncertainty and structural alternatives; and conditions that reverse the result.
Keep health outcomes, resource savings, prices/transfers, and business returns
separate. Cite the loop, externality, input, and test IDs that produced the result.
