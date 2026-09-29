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
### Limit
Period measures are not individual lifespan predictions. The modeled healthy state is not general disability-free health. Synthetic effects remain validation-only.
