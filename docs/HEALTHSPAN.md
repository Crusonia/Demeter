# Healthspan and time in health states

Demeter's primary `healthspan` metric is **remaining period years in the modeled
healthy state**. It is the same quantity as `metabolically_healthy_life_expectancy`,
whose name remains available for compatibility. The healthy stock is currently a
synthetic normoglycemic proxy. These outputs are validation-only: they do not
estimate freedom from every chronic disease, an individual's lifespan, or a
validated benefit from changing diet.

## Period calculation

For life-table survivors `l_x`, person-years `L_a`, and mutually exclusive state
shares `p_as`, the Sullivan calculation is:

`E_s(x) = sum_{a >= x}(L_a * p_as) / l_x`.

`healthspan = E_healthy(0)` and `life_expectancy = sum_s E_s(0)`.
`t2d_free_life_expectancy = E_healthy(0) + E_insulin_resistant(0)` includes the
IR/prediabetes proxy; it is not freedom from all chronic disease. The model also
reports each state's remaining years, including modeled T2D years. Each age's
conditional values appear in `healthspan.period_by_age`. Zero survivorship makes
conditional expectancy undefined (`null`), whereas zero healthy prevalence is a
real zero contribution. Invalid or overlapping partitions are rejected.

This calculation freezes the current mortality and prevalence schedules. It
does not follow a birth cohort through future changing schedules, and healthy
years can include time after a return from IR. It is not age at first disease.
Empty current-age cells use the engine's disclosed reference shares. The 100+
tail retains the existing fixed-state approximation in [MODEL_SPEC.md](MODEL_SPEC.md).

## Time experienced by the simulated cohorts

`healthspan.restricted_cohort` follows the original 101 age groups through the
simulation, retaining their identities after they enter the pooled 100+ stock.
Death ends time accrual. Over one annual step, constant state mortality hazard
`h` and starting stock `N` contribute `N * (1 - exp(-h)) / h` person-years;
the zero-hazard limit is `N`. Metabolic transitions occur at year end, so a
transition cannot reassign time already lived during that year.

The report gives state person-years, years per initial person, survivors,
deaths, and cumulative transitions by initial age. Annual
`restricted_healthy_years` is cumulative healthy person-years divided by the
initial population. All these quantities are restricted to the selected horizon;
they do not extrapolate lifetime healthspan. An empty initial group has an
undefined mean (`null`). Population and transitions reconcile with the engine.

## State changes, competing risks, and unavailable measures

The following three-state description applies to `health_structure: legacy`.
The optional [PreChronic structure](PRECHRONIC.md) supplies a separate state,
competing reversal/progression, and period/restricted PreChronic years. Its
metric contract marks that measure available while retaining the broader
clinical and disability restrictions.

Mortality is applied first. Among survivors, healthy people can enter IR, and IR
people can return to healthy or enter T2D through competing transition hazards.
An IR survivor cannot take both exits in one step. T2D has no remission pathway;
its only exit is mortality. These rules describe the existing annual operator
sequence, not a continuous-time joint disease process.

The three stocks are mutually exclusive. The model has no overlapping diagnoses,
ascertainment process, or representation of non-T2D chronic disease. The metric
contract therefore records reasons that PreChronic years, all-chronic-disease-free
years, diagnosed-chronic-disease years, QALYs, and WHO HALE are unavailable. It does
not substitute zero or a utility weight of one. PreChronic requires a separate
state definition and evidence mapping; quality/disability adjustment requires
sourced weights and explicit treatment of multimorbidity. WHO's
[HALE definition](https://www.who.int/data/gho/data/indicators/indicator-details/GHO/gho-ghe-hale-healthy-life-expectancy)
has a broader morbidity/disability scope than this metabolic proxy.

## Reproducible check against published health expectancy

The shared estimator reproduces all 18 age-specific healthy-life-expectancy
values in CDC/NCHS [Statistical Notes 21, Table 2, printed page 6](https://www.cdc.gov/nchs/data/statnt/statnt21.pdf)
at their published one-decimal precision. The example is U.S. White females in
1995 and defines health as self-reported good-or-better health. Those definitions
are retained; the example is not a current national metabolic calibration.

The immutable PDF and source receipt live in
`data/sources/healthspan/nchs-2001/`. The registered dataset
`healthspan_method_benchmark` specifies population, definitions, uncertainty,
extraction page, ages, and role `method_validation_only`. The transform verifies
the source checksum and rebuilds derived JSON and its manifest in
`src/demeter/data/bundled/`. The PDF is included in the source distribution;
the derived bundle ships in the wheel. Tests reproduce the bundle offline and
reject corrupted bytes. This verifies estimator arithmetic, not dietary effects
or the clinical validity of the model's healthy state.

## Uncertainty and scenario accounting

Seeded uncertainty runs use identical parameter draws for baseline and
intervention. They report period healthspan and restricted cohort healthy-time
intervals by age, as well as scalar outcome intervals and paired differences.
These are parameter-sampling intervals under the existing independent synthetic
distributions, not empirical confidence intervals. Initial shares, source
inputs, structural assumptions, and correlations remain outside that uncertainty.

Comparison exports absolute/relative healthspan differences, state person-year
differences, and cumulative transition differences. These connect later food
scenarios to inspectable state changes, but do not uniquely decompose causal
pathways. The [food-leverage report](LEVERAGE.md) adds an explicit counterfactual
pathway allocation with sampling intervals; it does not identify biological
mediation or establish empirical causal effects.
Evidence hashes, source vintages, scenario assumptions, metric definitions and
validation-only labels travel with the outputs.

```powershell
uv run demeter healthspan scenarios/baseline.yaml --output outputs/healthspan.json
uv run demeter evidence healthspan
uv run demeter data rebuild-healthspan --destination outputs/healthspan-rebuilt
uv run demeter compare scenarios/baseline.yaml scenarios/reduce_upf_30.yaml
uv run demeter uncertainty scenarios/reduce_upf_30.yaml --draws 128 --seed 42
uv run demeter sensitivity healthspan --samples 64 --seed 42
```

Full model calibration remains a separate, later validation pass. Scientific
mode stays disabled until the scientific acceptance criteria are satisfied.

## Design trace

This outcome interface supports the health component of Q-03/RM-04 in the
[problem boundary](design/01_PROBLEM_BOUNDARY.md), without implementing its payer
or funding decisions. It measures the existing L-00 transition-depletion
mechanics. The relevant input packages are I-01 (population/health), I-11
(measurement/reference data), and I-12 (experiment controls); no new externality
or economic feedback loop is added.

`sullivan` and `CohortTime` in `src/demeter/health/healthspan.py` implement the
F-01 accounting and F-08 measurement interfaces from the
[formulation contracts](design/05_FORMULATION_AND_TESTS.md).
`tests/test_healthspan.py` exercises T-01 conservation, T-02 zero/empty inputs,
T-03 finite-horizon and terminal-group accounting, and T-08 paired uncertainty.
The `healthspan_method_benchmark` dataset supplies an observed arithmetic
reference. It does not satisfy T-06 independent clinical holdout validation.
The annual operator timing and its limitations remain explicit; no time-step
convergence claim is added by this accounting change.
