# Flagship scenario: a shift toward real food

**Purpose:** help each participant in the agriculture, food, and health value
chain understand which changes create value, where that value appears, and how
they could capture a share of it. The shared learning objective is to understand
the levers connecting agriculture, food choices, health, and healthcare costs.

**Status:** a future integrated scenario brief. The current health engine supplies
part of the foundation; this scenario does not yet run. Its implementation follows
the scientific gates in the [program vision](PROJECT_VISION.md). The
[first software exercise](FIRST_EXERCISE.md) remains a validation-only introduction.

The [design inputs](design/README.md) translate this brief into a causal-loop
register, candidate positive/negative externalities, an input map, and equation/test
contracts. Those files feed implementation proposals while keeping premises visible.

## The question

> As people shift toward real food, what changes across agriculture, processing,
> distribution, retail, and healthcare? Which actions create value, who pays for
> them, who captures the benefits, and when?

A farmer considering a regenerative practice should eventually be able to trace
its potential value through the supply chain to retail and back to farm returns.
A retailer should be able to explore the product, price, and access changes that
could support sustained demand. A payer or employer should be able to examine
whether supporting dietary change in the PreChronic population could reduce
later disease-related spending enough to cover the intervention's costs.

These participants examine a common scenario from different positions. A benefit
to one actor can coexist with a cost or weak incentive for another. The model
should expose those differences and the contracts or constraints that explain them.

## Define the change before calculating its effects

"Real food" names the flagship direction. An executable scenario needs a specific
food basket and substitution pattern: what people buy and eat instead of what,
in what quantities, at what prices, and with what preparation and access needs.
Record measurable composition and processing attributes relevant to the question.
Then map changed intake to evidence-supported exposures and endpoints.

Keep production practice, product attributes, marketing claims, purchase behavior,
and biological exposure separately identifiable. A regenerative label does not
itself supply a nutrient change, consumer premium, or health-effect coefficient.
The current relative UPF reduction example does not define the whole real-food
transition and must not be relabeled as its validated proxy.

Likewise, a regenerative scenario must specify the practice, crop/product,
location, comparison, measured attributes, verification, and transition costs.
Where a necessary relationship is unknown, leave it unresolved and identify the
evidence needed to test it.

## Give each participant a decision and a result

The future scenario should provide a view for every relevant part of the chain:

| Participant | Example action to examine | Value and costs to follow |
| --- | --- | --- |
| Farmer and agricultural service/input supplier | Change a specified practice or provide technology that enables it. | Yield, inputs, transition risk, verification costs, farm price, and retained margin. |
| Processor and food manufacturer | Preserve product identity, change formulation, or add capacity. | Product attributes, throughput, conversion cost, waste, wholesale revenue, and margin. |
| Distributor and logistics operator | Change sourcing, aggregation, or delivery. | Availability, delivered cost, spoilage, working capital, and service revenue. |
| Retailer and food-service operator | Change assortment, merchandising, preparation, or price. | Sales, repeat purchases, substitution, procurement cost, waste, and margin. |
| Household | Change its food basket and sustained consumption. | Food spending, time, access, preferences, and evidenced health outcomes. |
| Clinician and healthcare provider | Identify earlier risk and deliver a defined intervention. | Reach, engagement, health outcomes, service revenue, delivery cost, and capacity. |
| Payer, employer, or public program | Fund prevention or change payment terms. | Program cost, covered utilization, net spending, retention, and the timing of benefits. |
| Capital or infrastructure provider | Finance a transition, pilot, or capacity expansion. | Capital required, contractual cash flows, risk, and the option to expand or exit. |

Show incremental results against the same counterfactual, by actor and time
period. Keep revenue, resource costs, margins, health outcomes, and transfers
distinct. A retail premium is not all farmer income; a payment between two
participants must not be counted twice as new system value. Healthcare savings
do not become food-company revenue without a mechanism connecting them.

## Example: regenerative production to retail value capture

Start with a named producer's proposed practice change. Follow its effects on
cost, yield, risk, and any measured product attributes. Then examine whether
verification, identity preservation, processing, and distribution allow those
attributes to reach a retailer and be understood by buyers.

Compare conditions with and without repeat demand or a premium. Trace any change
in price and volume through retailer and intermediary costs and margins. Use
explicit procurement/offtake terms to show how much value returns to the producer
and the suppliers enabling the change. Include transition time, capital needs,
substitution away from other products, and the possibility of no added net value.

The commercial pathway and the health pathway require separate evidence.
Consumer willingness to pay does not establish a health benefit. A demonstrated
health benefit also does not establish who captures a commercial return.

## Central health question: intervene before chronic disease

The project aims to understand **whether, how, and under what conditions targeting
the PreChronic population can reduce healthcare costs**. The
[existing roadmap](POST_V0_1_ROADMAP.md#step-2--make-prechronic-a-first-class-cohort)
uses PreChronic for earlier metabolic risk before diagnosed chronic metabolic
disease, potentially before formal prediabetes thresholds. It is a proposed
modeling concept requiring explicit, validated inclusion criteria for each
analysis. It is broader than a single laboratory cutoff and is not a universal
diagnosis or a separate state in today's engine.

The future analysis should trace:

```text
defined earlier-risk population
    -> identification and enrollment
    -> access to a specified food intervention
    -> sustained dietary change
    -> evidenced changes in progression or recovery
    -> disease-related utilization and healthcare spending
    -> allocation of costs and benefits through payment arrangements
```

Each arrow is a relationship to establish and test. Compare targeting this
population with a defined usual-care counterfactual and, where supportable,
broader or later intervention. Account for identification errors, reach,
persistence, intervention/delivery costs, benefit delays, and movement between
payers. Report absolute health effects, gross spending changes, and net costs
over a stated horizon. Report longer-term costs separately when supported;
avoided disease events alone do not establish net lifetime savings.

The intended analysis should reveal who has an incentive to fund prevention and
whether a payment arrangement could connect health value with food-system action.
The cost reductions are a research objective to evaluate, not an assumed result.

## What a participant should learn from the future exercise

1. Choose a role and a feasible lever; predict its effects across the chain.
2. Compare specified real-food transition paths, including slow adoption,
   constrained supply, and no meaningful health or commercial improvement.
3. Inspect where value is created, who bears the costs, who captures returns,
   and how delays, contracts, and bottlenecks change the result.
4. Examine which agriculture–food–health links explain the outcomes, including
   the PreChronic intervention and healthcare-cost pathway.
5. Identify a decision that changes under different assumptions and the next
   observation that would most improve the analysis.

Unresolved design work includes the reference basket, measurable exposure changes,
geography and horizon, PreChronic inclusion criteria, and source-supported
commercial and clinical relationships. Propose these as reviewable evidence and
scenario specifications. No new clinical state, economic equation, or numeric
effect is activated by this brief.
