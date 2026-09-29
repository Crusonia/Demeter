# Chart teaching notes

Reviewed learning content for the local interface and offline reports. Sections
are matched to stable figure IDs (a trailing * matches a chart family). These
explain model behavior; they are not claims about a dietary intervention.

## stocks
### Question
Where does the population go over time?
### Read
Each colored area counts people in one modeled health state. Read the total at the top of the stacked areas, not by adding the heights of their upper edges.
### Mechanism
This is a closed population. People age and move between states; deaths leave the living population. There are no births or migration, so a declining total is expected. This is not a U.S. population forecast.
### Try
Predict which state will change most when UPF exposure is reduced. Change only that exposure, run the model, and compare with the frozen reference.
### Predict
Before changing exposure, predict which stock moves first and whether the total living population changes in the same direction.
### Challenge
A smaller disease stock can also result from more deaths. Inspect entries, exits and deaths before calling it improvement.
### Evidence
Repeated observations of the same people, with diagnosis, treatment and deaths, could constrain transition rates. A cross-sectional share alone cannot.
### Limit
State allocation and transition rates remain synthetic. A smaller disease stock can reflect recovery, mortality, or fewer entries; inspect flows before interpreting it as improved health.

## flows
### Question
Which movements explain the changing stocks?
### Read
These are people moving during each annual step, not the number currently in a state. Year zero is the starting snapshot.
### Mechanism
A stock accumulates inflows and loses outflows. Progression, recovery, aging, and death have different meanings even when their totals look similar.
### Try
Compare progression and death flows with the living-stocks chart. Explain why a falling stock does not necessarily mean fewer new cases.
### Predict
If the recovery rate rises while everything else is fixed, predict the next annual inflow and the later stock response.
### Challenge
Question whether the recovery definition in a study matches the destination state here.
### Evidence
A longitudinal transition table with follow-up time, competing deaths and missingness would be more informative than a before/after prevalence difference.
### Limit
These are modeled transitions with synthetic clinical rates, not observed incidence.

## transitions
### Question
How can people move through this model?
### Read
Nodes represent health states and arrows represent implemented flows. Hover to see the parameter behind a link.
### Mechanism
Every transfer removes people from one stock and adds them to another or to an explicit death sink. The diagram is drawn from the engine's actual structure.
### Try
Find a recovery pathway. Change its synthetic rate in Advanced assumptions and predict which other stocks will respond.
### Predict
Choose one arrow and predict which stock loses people and which gains them.
### Challenge
Select that arrow in Sources. Is its parameter synthetic, estimated or observed? A missing arrow is a scope decision.
### Evidence
Evidence would need to identify that transition in the relevant population and time unit, including reversals and competing events.
### Limit
An implemented arrow does not establish a real-world causal effect. Missing arrows describe scope, not evidence that an effect is zero.

## dependencies
### Question
Which assumptions connect a food change to an outcome?
### Read
Follow the arrows from an input toward a modeled outcome. Dashed amber links depend on synthetic inputs; hover for evidence metadata.
### Mechanism
The graph records implemented dependencies. A food change affects transitions through specific coefficients and delays before it can affect state composition and mortality.
### Try
Choose one arrow and inspect its evidence before changing the corresponding assumption.
### Predict
Choose a food-to-outcome route and predict the sequence and timing of changes before running it.
### Challenge
Inspect the weakest link in Sources. A plausible mechanism or fitted association does not establish a causal intervention effect.
### Evidence
A specified intervention, comparison, population, outcome and follow-up are needed for each link. Explain which study design could distinguish the link from confounding.
### Limit
Dependency, association, and established causation are different. This graph is not the complete agriculture-food-health system.

## cohort_*
### Question
How do age and model time interact?
### Read
Color shows the count in a particular age cell and health state. The axes are age and simulation year; the 100+ cell pools ages.
### Mechanism
People move to older age cells each year while transitions and deaths change their health states.
### Try
Trace a diagonal across age and time, then compare it with the overall state totals.
### Predict
Predict where a starting age group appears after one model year.
### Challenge
Check the pooled oldest-age cell and the absence of births or migration before interpreting the pattern as a national forecast.
### Evidence
Age-specific observations and evidence about transport between calendar years would be needed to compare these modeled cells with a changing population.
### Limit
These are age-cell histories, not identified birth-cohort survival curves. The oldest cell is pooled.

## uncertainty_*
### Question
How much do results vary across the stated assumptions?
### Read
The central line is a sampled median and the band shows the exported quantiles. It is not a confidence band for a verified causal effect.
### Mechanism
Python reruns the model with the registered parameter distributions. The viewer does not resample or invent uncertainty.
### Try
Compare Preview with Standard sampling. Then inspect which synthetic range contributes to the spread.
### Predict
Predict whether changing a nominal value without changing its sampling distribution will move the sampled band.
### Challenge
Inspect the sampled inputs in Sources. Which source uncertainty or dependence between parameters is missing?
### Evidence
Joint parameter uncertainty, better-supported ranges and tests of alternative equations could change the spread. More draws alone cannot establish validity.
### Limit
These runs assume independent parameters and omit important structural and source uncertainty. The median need not equal the nominal result. Subtracting two bands does not produce an interval for their difference.

## sensitivity
### Question
Which uncertain assumptions drive variation in this experiment?
### Read
Bars show Sobol total-order indices and their reported uncertainty. Indices include interactions and need not sum to one.
### Mechanism
Sensitivity depends on the chosen ranges, outcome, and model structure. It measures variation in this model, not causal evidence strength.
### Try
Find the largest uncertain bar and inspect its parameter range. Ask whether better evidence could narrow it.
### Predict
Predict which assumption will rank highest, then compare your guess with the reported uncertainty in its index.
### Challenge
Would the ranking change if another plausible range or model structure were used? A high rank is not strong causal evidence.
### Evidence
Evidence that narrows an important range or identifies parameter dependence could change the ranking; independent outcome validation would test whether the model predicts well.
### Limit
Small sample runs can produce noisy or negative estimates. Do not turn this ranking into a policy or investment recommendation.

## parameter_*
### Question
What assumptions were actually sampled?
### Read
The histogram shows draws used in this run. Check the parameter name, unit, evidence status, and range.
### Mechanism
The nominal parameter controls the single deterministic trajectory; a distribution controls uncertainty runs. Changing the nominal value alone does not move the distribution.
### Try
In Advanced assumptions, change a nominal value within its range. Explain why the nominal trajectory can move while the uncertainty band stays similar.
### Predict
Predict how changing only the nominal value differs from changing the distribution used for sampling.
### Challenge
Check whether the saved range is empirical uncertainty or a synthetic software experiment.
### Evidence
An appraised estimate with matching units, population and estimand, including uncertainty and covariance, could replace a synthetic range after validation.
### Limit
Synthetic ranges are software experiments, not empirical confidence intervals. They must not be represented as observed evidence.

## history_*
### Question
How well did simple forecasts track historical observations?
### Read
Separate observed points, forecasts, and their intervals. Hover for forecast origins and inspect breaks in measurement definitions.
### Mechanism
Forecasts use earlier data and are evaluated on later observations. Definition segments are kept separate.
### Try
Find a period where prediction and observation diverge. Inspect the residual and its source rather than explaining it with the food model.
### Predict
Before inspecting a later observation, predict whether the earlier trend continues and how wide its forecast interval should be.
### Challenge
Check definition breaks, data revisions and omitted shocks. Do not attribute a residual to diet without a model that identifies that effect.
### Evidence
Additional comparable observations and a prespecified future evaluation can test forecasting. Dietary causality requires separate evidence.
### Limit
These are historical benchmark checks, not a backtest of dietary causality. Missing intervals mean insufficient history, not zero uncertainty.

## diet_*
### Question
Why can an intervention's effects arrive or fade slowly?
### Read
Distinguish the specified exposure path, effective response, exposure memory, and cumulative time in each condition. The historical lag challenge is a separate observed benchmark.
### Mechanism
The optional timing model includes adjustment and fading memory. Response and recovery can follow different delays.
### Try
Move the intervention start year, add a return to the reference exposure, and predict when the response will peak or fade.
### Predict
Predict when the response peaks and whether it persists after the input returns to its reference level.
### Challenge
Could a different delay or memory assumption produce a similar curve? The historical shortcut challenge does not identify a national dietary lag.
### Evidence
Repeated exposure and outcome measurements with treatment, adherence and competing-event histories would help distinguish delay from selection or changing intervention intensity.
### Limit
Timing parameters remain synthetic. Historical challenge curves are not model remission predictions or evidence for the selected lag.

## glp1_*
### Question
How do access, persistence, and capacity shape treatment exposure?
### Read
Distinguish treatment stocks, starts and stops, response proxies, and capacity. Trial contrasts are separate benchmarks with their own populations and follow-up periods.
### Mechanism
The model applies specified access, coverage, copay, and capacity paths to synthetic initiation, discontinuation, and response rules.
### Try
Reduce supply without changing coverage. Then restore supply and compare treatment counts with the response curve.
### Predict
Predict the direction of treatment starts, stops and response when supply falls but coverage remains fixed.
### Challenge
Compare the saved trial eligibility and estimand with the modeled population. Trial weight change does not identify a diabetes transition hazard.
### Evidence
Applicable initiation and persistence observations, plus an independently validated weight-to-health bridge, would be needed to replace these synthetic dynamics.
### Limit
These are validation-only treatment dynamics, not clinical forecasts or payer-cost estimates. Price is an input, not an economic forecast.

## *
### Question
What does this measure tell us about the model?
### Read
Check the chart title, axes, units, legend, selected scenario, and time horizon. Use Data to inspect the plotted values.
### Mechanism
This view is calculated by the canonical Python analysis. Period life expectancy freezes the current mortality schedule; healthy-state years use the model's state definitions.
### Try
Compare the frozen reference with one changed assumption. Follow the related state or mortality pathway before explaining the difference.
### Predict
Predict how one specified assumption changes this measure before looking at the rerun.
### Challenge
Trace the result through its saved inputs. Which assumption would most undermine your explanation if it were wrong?
### Evidence
Name the missing observation or study design, including population, units and time period, that could discriminate between competing explanations.
### Limit
Period measures are not individual lifespan predictions. The modeled healthy state is not general disability-free health. Synthetic effects remain validation-only.
