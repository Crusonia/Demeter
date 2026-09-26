# System levers and changing trends

Demeter should help identify actions that change an outcome and the conditions under which those actions work. The examples below define a research agenda; the current prerelease does not implement these integrated market scenarios.

## A lever has an actor

A **lever** is an action a specified actor can take: change a product, fund a benefit, adjust procurement, redesign a contract, or add capacity. An **external trend** is something that actor must respond to: treatment prices, income, a competitor's entry, or a policy change. The same variable can be a lever for one actor and external for another.

A **constraint** limits the response: a budget, eligibility rule, production lead time, distribution gap, or weak adherence. An **indicator** provides evidence about the state of the system. Keeping these roles separate makes scenarios interpretable.

## Candidate levers and their causal paths

| Actor and lever | Path to test | What could weaken or reverse the result? |
| --- | --- | --- |
| Payer or employer funds a targeted food benefit | Access and relative price → purchases → sustained dietary exposure → metabolic transitions → utilization | Low reach, substitution outside the target basket, short enrollment, high administration cost, or weak effects. |
| Food company changes formulation, price, or portion format | Product attributes → acceptance and substitution → intake → health and commercial outcomes | Customers switch products, compensating intake elsewhere, poor taste, input scarcity, or margin compression. |
| Retailer improves availability and convenience | Local access and preparation burden → repeat purchases → food basket | Affordability remains binding, spoilage rises, or adoption fades. |
| Buyer commits to procurement or offtake | More predictable demand → financing and capacity → supply and price | Uncertain renewal, concentrated buyers, a long build period, or adverse demand changes. |
| Farmer changes crop or production practice | Costs, yields, soil, and composition → supply, prices, margins, and exposures | Transition losses, inadequate evidence on composition, unavailable processing, or no durable premium. |
| Payer and provider change payment terms | Incentives and retained benefit → prevention adoption → utilization and capacity response | Measurement errors, adverse selection, delayed savings, or persistent fixed costs. |

Each row requires multiple estimated links. A plausible story is the starting hypothesis, not evidence that the full pathway works.

## Trend scenarios that could change the opportunity set

### GLP-1 price, access, and persistence

Compare conditional paths for eligibility, effective out-of-pocket price, coverage, initiation, persistence, discontinuation, and treatment response. Examine food quantity and category demand separately. Link direct treatment effects and changes mediated through diet without double counting them.

Possible questions include whether changed demand creates a need for different food formats, nutrition support, distribution, or capacity. Include stalled access, low persistence, competitor response, and no meaningful category shift. The model should allow an opportunity to disappear.

### Relative food prices and household constraints

Compare scenarios where nutrient-dense options become more affordable, remain at a premium, or face a supply shock. Test own-price and cross-price responses alongside income, convenience, availability, and habit. Demand may move between categories without producing the assumed nutritional change.

### Earlier identification and PreChronic intervention

Explore an earlier-risk population before diagnosed chronic disease. **PreChronic is a proposed modeling concept**, requiring explicit and validated inclusion criteria for each analysis. It is not yet a separate state in the current engine or a universal clinical diagnosis.

Test detection, enrollment, sustained engagement, progression, and supported reversal. More screening need not mean more effective prevention. Report misclassification, access, participation cost, and the time until a potential benefit reaches a payer or provider.

### Reimbursement and the allocation of savings

Vary the payer, eligible population, payment structure, contract duration, and share of savings retained by the party funding prevention. Evaluate a durable benefit, a limited pilot, delayed adoption, and withdrawal. A positive population outcome may still lack a viable payment mechanism.

### Measurement, production, and distribution technology

Test whether better measurement reduces an important uncertainty; whether new processing or distribution capacity changes delivered cost; and whether agricultural practices change measurable composition, yields, or risk. Keep unverified soil-to-nutrition-to-health links as explicit hypotheses. Also test failure to improve cost, quality, or adoption.

## How to discover leverage

1. **Define the outcome and actor.** Improving population health, reducing a payer budget, and earning a producer margin are different objectives.
2. **Specify a feasible action.** Include reachable scale, cost, lead time, target population, and operational limits.
3. **Trace the mechanism.** Show every intermediate step and the evidence needed for it.
4. **Compare a counterfactual.** Hold unrelated assumptions consistent and account for displaced spending or alternative uses of capacity.
5. **Vary uncertain conditions.** Include interactions, correlated trends, lags, and alternative model structures.
6. **Look for thresholds and reversals.** Identify when the preferred action changes and how uncertain that boundary is.
7. **Test robustness.** Favor conclusions that survive plausible alternatives; expose fragile ones and the evidence that would resolve them.

Sensitivity analysis identifies parameters that explain variation under a chosen set of ranges and distributions. A sensitive parameter is not automatically an actionable lever. It may be uncontrollable, expensive to change, or influential only because an arbitrary uncertainty range was wide. A lever comparison additionally needs intervention feasibility, causal support, cost, and timing.

[Tornado diagrams](Visualization-and-Tornado-Diagrams.md) should be a standard view of these comparisons. They show signed output changes for explicit low and high input settings, ranked by effect span. Readers should be able to trace a bar back through the relevant equations, delays, constraints, and evidence. Paired with causal maps and interaction plots, they help explain why a modeled outcome changes and where a decision is fragile.

## Minimum scenario specification

Every proposed scenario should document:

- decision-maker, target population, geography, baseline year, and horizon;
- the lever, its cost, timing, scale, and what remains fixed;
- external trend paths, including stalled or reversing conditions;
- causal links, evidence status, units, and uncertainty;
- adoption, persistence, substitution, capacity, and feedback;
- outcomes by actor, cohort, and time period;
- the comparison strategy and criteria that would change the decision;
- observable signals and when the decision-maker receives them.

Keep unsupported numeric values out of the evidence-backed model. A synthetic software example must be labeled and isolated from substantive findings.

See the [scenario catalog](https://github.com/Crusonia/Demeter/blob/main/docs/SCENARIO_CATALOG.md) for the wider research surface and [real options](Real-Options-and-Strategic-Value.md) for decisions that adapt to new information.
