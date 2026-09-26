# Visualization and tornado diagrams

**Tornado diagrams should be a core Demeter diagnostic for understanding what drives a modeled outcome and which assumptions could change a decision.** This page specifies planned behavior; chart generation is not yet implemented in v0.1.0a1.

The chart should answer: which input changes move this outcome most, in which direction, across which ranges, and through which modeled mechanisms?

## How to read the chart

A conventional tornado diagram places inputs on the vertical axis and a common output metric on the horizontal axis. Each row shows the output produced by a specified low and high setting of that input. A reference line shows the baseline output. Rows are ordered by the span of the endpoint results, largest first.

Both endpoints can fall on the same side of the baseline in a nonlinear model. Increasing an input may also reduce the output. Mark low-input and high-input endpoints explicitly rather than assuming that left always means a lower input or that right always means improvement.

Every diagram must state:

- the question, population or decision-maker, geography, and horizon;
- the output definition and units, including whether the axis shows levels or changes;
- baseline values and the low/high settings for each input;
- why those ranges were chosen and whether they describe feasible interventions or uncertain estimates;
- what was held fixed, what was allowed to respond, and the treatment of feedback;
- source/model version, evidence status, and important omitted uncertainty.

A bar is a sensitivity result under those conditions. Its endpoints are not a confidence interval unless a separate, justified statistical calculation defines them as such.

## Three useful views

| View | Rows | Horizontal axis | Decision it helps inform |
| --- | --- | --- | --- |
| **Outcome sensitivity** | Uncertain transition, exposure, adoption, cost, or behavioral parameters. | One defined health or economic output at one horizon. | Which assumptions need closer examination? |
| **Feasible lever comparison** | Explicit interventions by a named actor, each with a realistic scale and cost. | Change relative to a common counterfactual. | Which actions merit further evaluation, given feasibility, cost, and evidence? |
| **Strategy sensitivity** | Assumptions affecting the relative merits of fixed and adaptive choices. | Net value difference between specified strategies, or separately calculated net option value. | Which assumptions change the preferred choice or justify learning first? |

Keep these views separate and label them. Arbitrary parameter ranges can make a parameter appear influential without establishing that anyone can change it. A chart of intervention effects requires a causal and operational specification beyond parameter sensitivity.

## From a bar to cause and effect

A reader should be able to follow each bar into a pathway view: the changed input, affected equations, intermediate states, delays, feedback, and final output. Evidence annotations should distinguish observed inputs, estimated relationships, derived quantities, assumptions, and synthetic placeholders.

For example, a proposed food-benefit lever could follow relative price through purchases, substitution, sustained intake, metabolic transitions, and later utilization. The chart should expose whether the result depends mostly on uptake, persistence, a weakly evidenced health effect, or a payment assumption.

The diagram helps explain **cause and effect as represented in the model**. Establishing that the same causal effect holds in the world requires evidence and validation. Association alone cannot supply an intervention effect.

## Computation and comparison rules

1. **Choose the output first.** Use separate charts for disease prevalence, healthy-state years, household cost, payer spending, and enterprise value. Never mix incompatible units on a single axis.
2. **Define a reproducible baseline.** Record the scenario, parameter set, horizon, model version, and seed where relevant.
3. **Set interpretable ranges.** Cite evidence intervals or specify feasible intervention magnitudes. Label judgmental ranges. Do not compare rankings from different ranges as though they were intrinsic properties of the system.
4. **Run controlled variations.** Change one input at a time for the basic tornado, holding other exogenous assumptions fixed while allowing modeled endogenous responses and feedback to operate. Do not inadvertently freeze a mediator needed for the effect being tested.
5. **Respect dependence.** If inputs cannot plausibly vary independently, use explicitly labeled joint scenarios or conditional variations. Show the changed set instead of presenting the result as one isolated input's effect.
6. **Use paired stochastic comparisons.** Evaluate baseline and variation with common random draws where appropriate. Report simulation noise separately from the effect of varying the input.
7. **Check nonlinear behavior.** Evaluate intermediate points when justified. Endpoint ordering can hide a turning point, threshold, or discontinuity; flag these and provide a response curve.
8. **Rank transparently.** Order by endpoint span, label exact endpoints and baseline, and offer an accessible data table. Also show whether an effect changes sign or crosses a decision threshold.
9. **Retain the audit trail.** Export the input settings, results, ranges, evidence references, and chart metadata together. The visualization consumes canonical model outputs and does not reimplement the equations.

## A tornado for option value

Suppose an eventual analysis compares a pilot with an expansion right against committing to dedicated capacity now. Rows might vary retained demand, attainable margin, build lead time, flexibility cost, competitive entry, or the duration of reimbursement.

For a chart of **adaptive-strategy value minus immediate-commitment value**, the zero line marks equal modeled value. A row crossing zero identifies an assumption range that could reverse the decision. Show the baseline difference as a separate reference when it is nonzero.

Hold the compared decision policies fixed when testing their sensitivity. If the model re-optimizes the policy at each setting, identify that as a different analysis. In either case, decisions must use only the information available at their decision dates.

To measure net option value, compare flexibility against the appropriate fixed-strategy benchmark and include its acquisition and preservation costs. A ranking of effects on revenue alone does not measure the value of the option.

## Companion visuals

Tornado diagrams should sit alongside:

- **Causal and stock/flow maps**, to inspect mechanisms and accumulated state.
- **Time paths**, to show delayed effects and changes in rankings across horizons.
- **Two-input response surfaces**, to show interactions, thresholds, and strategy regions.
- **Global sensitivity analysis**, to assess variance and interactions across a joint uncertainty design; current Sobol plumbing is an engineering foundation for this work.
- **Observed-versus-modeled plots**, to expose calibration and holdout errors.

Tornado bars do not add up to a total causal contribution when feedback or interactions are present. They also do not replace global uncertainty analysis. The useful combination is a clear pathway, a quantified sensitivity, and evidence supporting the modeled relationship.

## Release standard

Early chart plumbing may use synthetic fixtures for software validation, with **SYNTHETIC — SOFTWARE VALIDATION ONLY** shown prominently. Public substantive rankings must wait for the relevant parameters and pathways to pass their scientific gate. Each exported chart should preserve its evidence label and caveats, including when viewed outside the surrounding page.
