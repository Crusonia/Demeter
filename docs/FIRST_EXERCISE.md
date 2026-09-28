# First exercise: predict, run, inspect, revise

**Purpose:** learn how assumptions, state changes, and delays shape a result.
**Scope:** software-validation exercise using synthetic metabolic and dietary
parameters. Numerical differences here are not estimates of a diet's real effects.

Complete [setup](GETTING_STARTED.md) first. Run commands from the repository root.
You can do the exercise alone or compare predictions with a group.

This prepares you for the future [real-food value-chain exercise](REAL_FOOD_VALUE_CHAIN.md):
understand how a lever works before tracing its value across agriculture, food,
retail, and healthcare. Today's exercise only runs the health mechanics. It does
not model a regenerative product, retail value capture, or healthcare costs.
This exercise uses the canonical three-state model; the separate optional
[PreChronic experiment](PRECHRONIC.md) remains uncalibrated.

For a smaller stock/flow model and the full path through uncertainty, historical
diagnostics and custom modules, use the [learning path](LEARNING_PATH.md).

## Predict before running

The example compares the baseline with a relative 30% reduction in the model's
UPF exposure multiplier, from 1.0 to 0.7. It does not specify a measured food basket,
an adoption program, or a cost. Fiber and fruit/vegetable multipliers remain fixed.

Write down your expectation: would a change appear immediately or gradually?
Which states should change first? Does changing an exposure directly change life
expectancy, or must it act through other model quantities?

## Run the comparison

```text
uv run demeter compare scenarios/baseline.yaml scenarios/reduce_upf_30.yaml --output outputs/first-comparison.json
uv run demeter observe scenarios/reduce_upf_30.yaml --draws 4 --samples 8 --seed 42
```

Open `outputs/observability/index.html` using the platform-specific command in
the setup guide. Read the validation label first, then inspect population stocks,
transitions, mortality, the life table, and the dependency graph. Use
`outputs/first-comparison.json` for the baseline/intervention comparison.

## Follow one result back to its assumptions

Inspect `evidence/parameters.yaml`, or run:

```text
uv run demeter evidence audit
uv run demeter evidence applicability
```

Trace the exposure through its lag and progression multiplier, metabolic
transitions, state-sensitive mortality, and period life expectancy. Find which
links use observed inputs and which still use synthetic parameters. The
[model specification](MODEL_SPEC.md) explains the equations.

The small uncertainty and sensitivity runs only demonstrate mechanics. Their
sampled ranges are synthetic; they cannot establish a causal claim or a reliable
ranking of real-world interventions.

## Try a control experiment

Copy the intervention scenario to a new file:

macOS/Linux:

```bash
cp scenarios/reduce_upf_30.yaml scenarios/my_first_experiment.yaml
```

Windows PowerShell:

```powershell
Copy-Item scenarios/reduce_upf_30.yaml scenarios/my_first_experiment.yaml
```

In your text editor, give the copy a new `name` and description, and change only
`upf: 0.7` to `upf: 1.0`. Keep the horizon and all other settings the same. Then run:

```text
uv run demeter compare scenarios/baseline.yaml scenarios/my_first_experiment.yaml --output outputs/control-comparison.json
```

The outcome differences should be zero: changing a name does not change the
equations. If they are not zero, check the scenario settings and report a
reproducible bug. This is a control for the software, not evidence about a diet.

## Debrief

- How did the trajectory compare with your prediction?
- Which equation or parameter explained a surprising result?
- Which missing evidence would most affect whether you trusted that explanation?
- Which feedbacks are absent? Prices, household substitution, production response,
  and payer incentives are future mechanisms, not implicit parts of this run.
- What could a future exercise test once one of those mechanisms is supported?

Choose a role in the value chain and name the next link you would need to make
this useful for your decision. A producer might need to trace a practice through
retail demand and procurement terms. A payer might need a defined PreChronic
population, intervention reach and costs, and evidence linking changed progression
to spending. Explain how that link would connect your action to value created
and the share you could capture. Do not calculate a return from the current
synthetic health output.

Record the commit (`git rev-parse HEAD`), scenario, seed, changed assumptions,
observation, and remaining question. Share a short issue with those details.
The useful contribution is the reasoning and reproducible experiment; a large
numerical benefit from a synthetic parameter is not a finding.
