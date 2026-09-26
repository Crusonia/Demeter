# Evidence, model status, and the path forward

The public vision is broader than the current implementation. This page describes **v0.1.0a1**, an engineering prerelease. The [acceptance checklist](https://github.com/Crusonia/Demeter/blob/main/docs/V0_1_STATUS.md) and [evidence gaps](https://github.com/Crusonia/Demeter/blob/main/docs/EVIDENCE_GAPS.md) provide the detailed current record.

## What runs today

| Component | Status and interpretation |
| --- | --- |
| U.S. age and mortality foundation | Observed CDC/NCHS 2022–2024 mortality and Census Vintage 2025 population counts; 101 cohorts, ages 0–99 and 100+, with total/male/female runs. |
| Health-state mechanics | Three population-conserving states, deaths, and aging. Metabolic allocation, transition hazards, and mortality hazard ratios remain synthetic. |
| Dietary scenario plumbing | Relative UPF exposure can affect synthetic transition logic with a lag. This is a software exercise, not a validated causal dose-response model. Changes to fiber and fruit/vegetable exposure are currently rejected. |
| Life-table outputs | Independent period life tables and Sullivan-style years in the modeled healthy state. These are not individual lifespan forecasts or a general HALE measure. |
| Analysis tools | Scenario comparison, paired Monte Carlo uncertainty, Sobol sensitivity, prevalence discrepancy reporting, and a historical mortality persistence backtest. |
| Provenance | Typed evidence and scenarios, input manifests/checksums, source vintages, model metadata, and synthetic-input warnings. |

Births and migration are zero. Census data initialize a closed cohort; its later population is not a forecast of the United States. The current backtest tests carrying mortality forward, not a dietary intervention. The uncertainty tools currently vary independent synthetic ranges and do not capture all data, structural, or correlation uncertainty.

**Scientific mode remains disabled.** Successful software validation does not complete the scientific v0.1 acceptance criteria.

## What is planned

The program aims to connect validated health pathways to food affordability and substitution, production and distribution, agriculture, adoption, healthcare economics, and policy feedback. A distinct PreChronic cohort, GLP-1 intervention dynamics, scientific visualization, and more extensive historical reconstruction are research directions requiring their own definitions, evidence, and validation.

Market forecasts, provider financial projections, option valuation, and the public Demeter Simulator are not implemented in this prerelease. The guide's examples describe questions these future modules should support.

## Evidence must constrain the story

Substantive parameters belong in the evidence registry with units, definitions, population, geography, vintage, provenance, transformations, and uncertainty. Parameter status distinguishes observed, estimated, derived, and synthetic values. Evidence quality is recorded separately from effect size.

Associations must not silently become causal effects. A broad concept such as food quality needs measurable exposures. A production practice needs evidenced intermediate links before affecting health. Overlapping dietary and treatment pathways need explicit handling to avoid counting an effect twice.

When evidence is unresolved, the project should expose the gap and show why it matters. It should not tune inputs to produce a preferred Food is Health conclusion.

## Validation grows with scope

The immediate scientific gate is to resolve health-state definitions and prevalence, estimate defensible transition hazards and mortality relationships, encode study-compatible dietary exposures, and evaluate an independent health holdout.

Later modules need their own historical comparisons and held-out evaluation. Reconstructing history must account for changes in treatment, diagnosis, demographics, smoking, policy, and shocks where material. A model should not force food to explain all observed health changes.

Integrated scenarios also need unit and conservation checks, tests of feedback behavior, attribution, uncertainty propagation, and alternative structures. Decision rules require evaluation without future information leaking into earlier choices.

## Reading a future result

Every published result should state the model version and data vintage; baseline and counterfactual; target population; changed and fixed assumptions; horizon; uncertainty; evidence strength; extrapolation; and known validation failures. A conditional scenario is not automatically a forecast.

The [model specification](https://github.com/Crusonia/Demeter/blob/main/docs/MODEL_SPEC.md), [project vision](https://github.com/Crusonia/Demeter/blob/main/docs/PROJECT_VISION.md), and [scenario catalog](https://github.com/Crusonia/Demeter/blob/main/docs/SCENARIO_CATALOG.md) are the technical companions to this guide.
