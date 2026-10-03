# Inputs to Demeter's model design

These Markdown documents turn the [real-food value-chain objective](../REAL_FOOD_VALUE_CHAIN.md)
into reviewable inputs to model design. They preserve proposed feedback mechanisms,
externalities, boundary choices, required data, and tests before equations are
implemented. They are not executable parameters or evidence that a premise is true.

## Read and use in this order

| Document | Design decision it supports |
| --- | --- |
| [Problem, behavior, and boundary](01_PROBLEM_BOUNDARY.md) | Whose decision, which behavior over time, what is inside the model, and what is deliberately excluded? |
| [Causal-loop register](02_CAUSAL_LOOPS.md) | Which closed feedback hypotheses could explain that behavior; where are the stocks, delays, and failure conditions? |
| [Externalities and business mechanisms](03_EXTERNALITIES.md) | Who receives an unpriced benefit or bears a cost; what could connect that effect to an actor's incentive or revenue? |
| [Model-input inventory](04_MODEL_INPUTS.md) | What must be observed, estimated, initialized, controlled, or calculated endogenously? |
| [Formulation and validation contracts](05_FORMULATION_AND_TESTS.md) | What equations, units, interfaces, and experiments would make a selected mechanism testable? |
| [Stakeholder rigidities](06_STAKEHOLDER_RIGIDITIES.md) | Which beliefs that a better, cheaper system is impossible does a question test; which are real constraints and which are misperceived? |
| [Land use and nutrition trades](07_LAND_USE_AND_NUTRITION_TRADES.md) | How could development, productivity, co-use, demand and farm decisions change regional food/nutrient capacity and the allocation of value? |

For the current health slice, the [clinical observation contract](../CLINICAL_OBSERVATION_CONTRACT.md)
details the source, measurement, timing, likelihood and evaluation requirements
for I-01/I-05/I-07/I-11/I-12 and F-04/F-08. It feeds design; it does not implement
a clinical observation model or activate a parameter.

The [NHANES III repeat-FPG design](08_NHANES_III_REPEAT_OBSERVATIONS.md)
preserves the proposal for an observed-label falsification test, source fields,
intake choices and privacy requirements. The subsequent
[offline repeat-FPG benchmark](../NHANES_III_REPEAT_FPG.md) implements a finite
recorded-label diagnostic under its separately frozen protocol; it admits no
clinical hazards or engine initialization.

The [NHIS reported-diagnosis design](09_NHIS_REPORTED_DIAGNOSES.md) specifies a
separate diagnosed-type observation benchmark and a synthetic categorical
software witness. Unknown type and inconsistent questionnaire responses remain
explicit; no participant intake, survey estimate or clinical initialization is
implemented by that witness.

The [synthetic NHIS joint-ratio witness](10_NHIS_SURVEY_WITNESS.md) tests complete
record-category accounting and dependent survey-ratio arithmetic on in-memory
fixtures. It reuses the existing covariance kernel without NHANES inference
metadata; participant admission and NHIS interval policies remain unresolved.

The [HRS repeat-biomarker checkpoint](../HRS_REPEAT_BIOMARKER_SOURCE_CHECKPOINT.md)
feeds I-11 observation design with native/adjusted assay roles and unresolved
selection, specimen clocks and diabetes type. It is source discovery, not an
empirical intake or a clinical likelihood.

## Methodological basis

This is Demeter's application of a system-dynamics approach informed by Thomas S.
Fiddaman's published work. It is not a design authored or reviewed by him.

- Fiddaman demonstrates that the same causal-loop structure can produce different
  behavior when stocks, initial conditions, or equations differ. We therefore
  carry each selected loop into a stock/flow formulation and a test, rather than
  infer its outcome from its label. [Fiddaman, 2017](https://metasd.com/2017/04/the-ambiguity-of-causal-loop-diagrams-and-archetypes/)
- His integrated climate-economy work separates endogenous, exogenous, and excluded
  quantities and examines what feedback is severed by a boundary choice. Demeter
  uses that distinction for its food–health–economic interfaces; it does not
  import climate-model coefficients. [Fiddaman, 1997, pp. 64–68](https://metasd.com/wp-content/uploads/2010/06/FiddamanDissertation.pdf)
- Vensim's documentation pairs relationships with equations and units and calls
  for equation and dimensional checks. These practices apply to Demeter's Python
  engine without requiring a runtime or framework change.
  [Equations](https://vensim.com/documentation/20400.html),
  [model and units checks](https://vensim.com/documentation/20570.html)

The food-system loops and spillovers below are **our proposed mechanisms to
investigate**, not claims established by those methodological references.

## How these files feed implementation

For a proposed model change, record a traceable chain in its issue and PR:

```text
decision / behavior question (Q-, RM-)
    -> stakeholder rigidity being tested (B-), if any
    -> selected loop or open pathway (L-, P-)
    -> relevant externality / value-capture hypothesis (X-), if any
    -> input packages (I-)
    -> equations / interface and tests (F-, T-)
    -> exact evidence-registry keys, source snapshots, code, and test results
```

Choose one bounded mechanism. Appraise every material link, including opposing
evidence; specify units, stocks, flows, delays, and alternative structures; then
implement within the active phase. Record failed tests and rejected premises as
well as accepted ones. Stable IDs let later PRs replace a hypothesis without
erasing why it was considered. Link actual code/tests when they exist, not proposed
paths presented as implementation.

**Design status and evidence status are different.** A `premise` here has unresolved
causal applicability and magnitude. `Mechanics implemented` means code exists,
not that it is scientifically validated. Every substantive numeric parameter
still belongs in `evidence/parameters.yaml` with the existing `synthetic`,
`estimated`, `observed`, or `derived` status and its evidence grade. Do not add
`premise` as a runtime parameter status or use an unknown effect as zero.

The [program vision](../PROJECT_VISION.md), [architecture](../SYSTEM_ARCHITECTURE.md),
and [v0.1 boundary](../../AGENTS.md) remain authoritative. Broad loops can be
documented now; agriculture, behavioral agents, healthcare-cost models, policy,
and commercial valuation are not activated by this design work. The current
[model specification](../MODEL_SPEC.md) describes what actually runs.
