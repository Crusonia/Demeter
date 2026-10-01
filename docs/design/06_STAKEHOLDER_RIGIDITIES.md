# Stakeholder rigidities

Status: **candidate premises for appraisal**, not findings. This register records
beliefs that a better, cheaper, more productive food–health system is not
possible, who holds them, and how Demeter could test them. It feeds the
[causal-loop register](02_CAUSAL_LOOPS.md), [externalities](03_EXTERNALITIES.md),
[input inventory](04_MODEL_INPUTS.md), and
[formulation contracts](05_FORMULATION_AND_TESTS.md).

## Purpose and use

Demeter's goal is to resolve each rigidity: determine whether it is real, under
what conditions it holds or breaks, what breaking it costs, and who captures the
result. Resolving does not mean assuming the belief is wrong. Some rigidities are
biological or physical and will survive testing.

Register every rigidity; model selectively. A rigidity enters the model only when
it is selected for a question and traced through the design chain
(`B-` → `L-`/`P-` → `X-` → `I-` → `F-`/`T-` → evidence keys). Global sensitivity
analysis should decide which rigidities materially change the
[top-level metrics](../PROJECT_VISION.md#top-level-metrics) and deserve modeling first. Registering
all of them does not justify a model that represents all of them at once.

## Reading the register

- **Held:** how firmly the stakeholder holds the belief.
- **Assessed:** a provisional design judgment of how rigid the constraint
  actually is. It is not measured evidence and must be revised as evidence is
  appraised. **Reversed** marks a belief that a lever works easily where the
  evidence points the other way; the rigidity is the belief itself.
- **Direction:** most beliefs claim a change is impossible. A few (B-24, B-31,
  B-32, B-33, B-44) instead claim a fix or outcome is easy or assured; these
  are tested for whether the claimed lever holds.
- **Type:** the source of rigidity.
  - **Bio:** biological or physical. Hardest to move.
  - **Econ:** prices, costs, and scale. Moves with cost curves or demand.
  - **Inst:** rules, contracts, subsidies, scoring, and payment models. Moves
    when the institution changes.
  - **Mind:** narrative, habit, and professional norms. Rigid mainly in belief.
- **Tested through:** existing design IDs that would carry the test. Blank means
  no mechanism has been registered yet.

Cited studies are starting points for appraisal. Each must be verified against
the primary source and entered in `evidence/parameters.yaml` with population,
units, and uncertainty before it affects a model result.

## A. Producers and land

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-01 | Commodity row-crop farmers | Corn and soy are the only crops that pencil out. | High | Medium–high | Inst, Econ | Offtake contracts, diversified revenue insurance, transition finance; crop insurance and program payments currently favor commodities. | P-01, L-04, L-05, I-02, I-09 |
| B-02 | Row-crop farmers | Regenerative practice cuts yield. | High | Medium | Bio, Econ | Local, comparable trial data; transition-period losses are real and long-run effects are context dependent. | L-13, L-15, I-02 |
| B-03 | Specialty-crop growers | Fruit and vegetables cannot get cheaper; labor is the ceiling. | High | Medium | Econ | Harvest automation, guaranteed buyers, selected controlled-environment production. | L-01, L-04, I-02 |
| B-04 | Ranchers | Grass-finished beef cannot compete on cost. | High | Medium–high | Bio, Econ | A durable premium or verified climate or health payments; longer finishing and land needs are real. | P-01, X-P02, X-N02, X-N03 |
| B-05 | Absentee landowners | Soil investment is the tenant's problem. | Medium | Medium–high | Inst | Leases that share soil-value gains; a large share of U.S. farmland is rented, often on short terms (USDA TOTAL survey, 2014). | L-13, I-02, I-09 |
| B-06 | Farm lenders | Practice transition is a credit risk. | High | Medium | Econ, Inst | Observed transition cash flows and bridge-finance terms. | L-05, I-09 |
| B-07 | Seed, chemical, and fertilizer suppliers | Yield per acre is the metric that matters. | High | Low | Mind, Econ | Buyers paying for nutrient density or verified outcomes. | P-01, I-03 |
| B-08 | Farmworkers | Healthy-food production means low-wage manual labor. | Medium | Medium | Econ | Automation shifting work toward skilled operation. | I-02, I-09 |

## B. Processing and manufacturing

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-09 | Packaged-food manufacturers | Reformulation kills taste and sales. | High | Low–medium | Mind | Gradual, industry-wide reformulation that removes first-mover risk; the UK salt-reduction program coincided with a fall in population salt intake (He, Brinsden, and MacGregor, BMJ Open, 2014). | I-03, I-05 |
| B-10 | Packaged-food manufacturers | Shelf life requires ultra-processing. | High | Medium | Bio, Econ | High-pressure processing, fermentation, improved cold chains; preservation needs are real. | L-03, I-03, I-04 |
| B-11 | Packaged-food manufacturers | The margin is in branded ultra-processed food; whole foods are commodities. | High | Medium–high | Econ | Branded nutrient density, demand shifts among GLP-1 users, payers or institutions as buyers. | P-01, L-02, I-03, I-09 |
| B-12 | Meat and protein processors | Scale only works in large centralized plants. | Medium | Medium | Econ, Inst | Regional processing with anchor buyers; inspection rules are part of the constraint. | L-04, I-03 |
| B-13 | Flavor and ingredient suppliers | Consumers require high sugar, salt, and fat. | High | Low–medium | Bio, Mind | Preference thresholds adapt with sustained exposure; sodium preference shifted after a low-sodium diet (Bertino, Beauchamp, and Engelman, American Journal of Clinical Nutrition, 1982). Innate sweet preference is real. | I-05, I-06 |

## C. Distribution, retail, and food service

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-14 | Grocers | Fresh food means shrink; center-store products pay the bills. | High | Medium–high | Econ | Demand forecasting, predictable produce-prescription volume, fewer handoffs. | L-03, L-06, I-04 |
| B-15 | Grocers | Slotting economics favor large packaged-food brands. | High | High | Inst | A different buyer (payer, institution) or channel. | L-06, I-04, I-09 |
| B-16 | Distributors and cold chain | Fresh food to rural and low-density areas costs too much. | High | Medium–high | Econ | Aggregation, network redesign, institutional anchor demand. | L-03, I-04 |
| B-17 | Restaurants and quick-service chains | Customers order indulgence; healthy menus fail. | High | Medium | Mind, Econ | Defaults, portion changes, and demand from GLP-1 users. | L-06, I-05, I-06 |
| B-18 | Institutional food service | Per-meal budgets make scratch cooking impossible. | High | Medium | Inst, Econ | Kitchen capital and labor models; ingredient cost is often not the binding constraint. | I-04, I-09 |

## D. Households

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-19 | Consumers | Healthy food is more expensive. | High | Medium | Econ | Depends on the price unit: nutrient-dense foods often cost more per calorie but not per portion or weight (Carlson and Frazão, USDA ERS EIB-96, 2012). Time, preparation, and spoilage risk are real costs. | L-07, I-05 |
| B-20 | Consumers and public commentary | People are addicted to junk food. | High | Medium | Bio, Mind | Ultra-processed diets caused higher energy intake in an inpatient randomized trial ([Hall et al., Cell Metabolism, 2019](https://doi.org/10.1016/j.cmet.2019.05.008)), and a minority meet food-addiction criteria (Gearhardt et al., "Social, clinical, and policy implications of ultra-processed food addiction," BMJ, 2023). For most people, habit and environment dominate and preferences adapt. | I-05, I-06 |
| B-21 | Consumers | There is no time to cook. | High | Medium–high | Econ | Minimally processed convenience food; time poverty is real. | L-07, I-05 |
| B-22 | Consumers | Healthy food does not taste good. | Medium | Low | Mind, Bio | Repeated exposure and gradual default changes. | I-05, I-06 |
| B-23 | Consumers | Metabolic disease is genetic. | Medium | Low–medium | Bio | Genetic risk interacts with environment and diet. | I-07 |
| B-24 | Food-access advocates | Physical access is the main lever. | High | Reversed | Mind | Evidence that supply access explains a limited share of nutritional inequality (Allcott, Diamond, and Dubé, Quarterly Journal of Economics, 2019). The rigidity is the belief that access alone is sufficient. | L-06, L-07, I-05 |

## E. Health care

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-25 | Health insurers | Prevention savings go to the next insurer because members switch. | High | High | Inst | Longer-tenure products, multi-year contracts, outcome contracts, pooled prevention funds. | P-02, L-08, X-P04, I-08, I-09 |
| B-26 | Health insurers | Food is not a covered medical benefit. | High | Medium, falling | Inst | Medicaid waivers, Medicare Advantage supplemental benefits, in-lieu-of-services authorities. | P-02, L-10, I-08 |
| B-27 | Health insurers | The payback period is too long. | High | Medium–high | Bio, Inst | Targeting populations with near-term events; biological delays are real. | P-02, L-08, I-07, I-08 |
| B-28 | Self-insured employers | Health is not our business, and turnover erases any return. | Medium | Medium | Mind, Econ | Absenteeism and on-the-job productivity effects that pay back faster than claims. | P-02, I-09 |
| B-29 | Hospitals paid fee-for-service | We are paid to treat disease. | High | High | Inst | Value-based payment and capitation. | P-02, L-12, I-08 |
| B-30 | Physicians | Patients will not change their diet. | High | Low–medium | Mind | Intensive lifestyle intervention reduced diabetes incidence ([Diabetes Prevention Program, NEJM, 2002](https://doi.org/10.1056/NEJMoa012512)); a weight-management program achieved diabetes remission in a substantial share of participants ([DiRECT, Lancet, 2018](https://doi.org/10.1016/S0140-6736(17)33102-1)). Training and reimbursement are the binding constraints. | I-07, I-08 |
| B-31 | GLP-1 manufacturers and investors | Drugs make food irrelevant. | Medium, rising | Low–medium | Mind | Appetite suppression may create a window for dietary change and raise demand for nutrient density; drugs and diet may be complements. | I-05, I-07 |
| B-32 | Public-health agencies | Education changes behavior. | Medium | Reversed | Mind | Evidence that defaults, prices, and environments outperform information alone. | I-05, I-06 |
| B-33 | Health-system planners | Less chronic disease means less healthcare demand. | Medium | Reversed | Mind, Bio | Reallocation toward acute events, refractory and previously undiagnosed conditions, and care in added years of life; many preventive interventions add net cost ([Cohen, Neumann, and Weinstein, NEJM, 2008](https://doi.org/10.1056/NEJMp0708558)). The rigidity is the assumption that prevention always saves money. | P-02, P-04, I-08 |

## F. Government and policy

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-34 | Farm Bill coalition | Commodity programs and nutrition assistance must stay bundled. | High | High | Inst | Political coalition change; generally a constraint to work within. | I-09 |
| B-35 | Federal budget scoring | Prevention does not pay back within the scoring window. | High | High | Inst | Longer-window or dynamic scoring; benefits beyond the window receive little weight. | P-02, L-10, L-12 |
| B-36 | Nutrition-assistance administrators | Purchases cannot be steered. | Medium | Medium | Inst | Produce incentives and state purchase-restriction pilots. | L-07, I-05 |
| B-37 | Food regulators | Labels do not change industry behavior. | Medium | Medium | Inst | Labeling that induces reformulation even when consumer response is small. | I-03 |
| B-38 | Legislators | Food policy is politically unwinnable. | Medium | Medium, falling | Mind | Bipartisan attention to food and chronic disease. | L-10 |
| B-39 | Defense establishment | Recruit fitness is a recruiting problem. | Medium | Low | Mind | Framing military readiness as a food-system outcome; Department of Defense estimates show most young Americans are ineligible to serve, with overweight a leading disqualifier. | I-09 |

## G. Capital

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-40 | Venture capital | Food and agriculture are low-margin, low-multiple categories, and food tech has failed. | High | Medium | Econ, Mind | Business models that capture value through payers, outcomes, or verified attributes. | P-01, P-02, I-09 |
| B-41 | Private equity and packaged-food acquirers | Buy brands, not systems. | High | Medium–high | Econ | Systems that capture measurable, contractible value. | P-01, I-09 |
| B-42 | Public-market analysts | GLP-1 drugs are a threat to packaged food. | Medium, rising | Medium | Econ | Evidence that changed demand favors nutrient-dense products. | I-03, I-05 |
| B-43 | ESG and impact investors | Health and climate are separate investment buckets. | Medium | Low | Mind | Coupled accounting showing where health and climate outcomes reinforce or trade off. | P-03, X-P02, X-N02 |
| B-44 | Carbon-market participants | Soil carbon credits are a reliable revenue stream. | Low | High | Inst, Bio | Verification, additionality, permanence, and reversal risk are binding; the rigidity is underestimated rather than overestimated. | L-13, X-P02, X-N02, I-10 |
| B-45 | Philanthropy | Fund programs, not markets. | Medium | Low | Mind | Market mechanisms that persist after grants end. | I-09 |

## H. Knowledge and narrative

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-46 | Nutrition researchers | The evidence is too weak to act on. | Medium | Medium | Mind, Econ | Natural experiments, feeding trials, and longer cohort follow-up; partly true. | I-07, I-11 |
| B-47 | Agricultural research institutions | The research agenda is yield. | High | Medium | Inst | Funding for nutrient density, soil, and health outcomes. | L-15, P-05, X-P03 |
| B-48 | Microbiome researchers | It is too early for applications. | Medium | Medium | Bio | Separating agronomic applications from human-health claims, which carry different evidence. | L-15, P-05, X-P03 |
| B-49 | Environmental organizations | Livestock is uniformly harmful. | High | Medium | Mind | Context-specific accounting for grazing on land unsuited to crops versus confinement systems. | X-P02, X-N02, X-N03 |

## I. Land-use trade beliefs to investigate

The following are opposing proposed beliefs, not measured stakeholder attitudes.
Firmness and empirical assessment remain unassessed. Concern about identity,
livelihood or succession is a legitimate objective to represent, not evidence of
irrationality. Family ownership and commercial scale overlap; see the
[land-use brief](07_LAND_USE_AND_NUTRITION_TRADES.md).

| ID | Stakeholder | Belief | Held | Assessed | Type | What would move it | Tested through |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-50 | Landowners, food buyers and communities; actual holders to establish | Any energy/data-center/urban conversion materially threatens national food supply. | Unassessed | Unassessed | Econ, Bio, Inst | Comparable direct footprints, cumulative regional conversion, product capacity, water, trade and delivered nutrients. | Q-05, RM-06, L-16/L-17, P-06, I-13, F-09/T-09 |
| B-51 | Producers, planners and investors; actual holders to establish | Small national acreage shares, productivity gains or GLP-1 demand changes guarantee that conversion has no material cost. | Unassessed | Unassessed | Econ, Inst, Mind | Regional bottlenecks, category demand/intake, irreversible loss, tenure, income and succession effects; adverse/null cases. | Q-05, RM-06, P-06/P-07, X-N07, I-13, F-09/T-09 |

## Patterns to test

The matrix classifies each belief by what it claims (rows) and the assessed
evidence (columns). Firmness (**Held**) is recorded separately in the tables.

| Belief claims \ Assessment | Claim does not hold | Claim holds |
| --- | --- | --- |
| **Change is impossible** | Misperceived constraints; the main opportunity. Examples: B-07, B-09, B-20, B-22, B-30, B-43. Some are already eroding: B-26, B-38. | Structural locks requiring institutional design rather than persuasion. Examples: B-05, B-11, B-15, B-25, B-29, B-34, B-35. |
| **A fix or outcome is easy or assured** | Traps where optimism exceeds evidence. Examples: B-24, B-31, B-32, B-33, B-44. | Accurate optimism; not a rigidity, and not registered here. |

Two cross-cutting hypotheses explain many structural locks and should be tested
explicitly:

1. **Incidence mismatch.** The actor who pays for a change is often not the actor
   who captures the benefit. See the [externalities register](03_EXTERNALITIES.md).
2. **Horizon mismatch.** Insurer tenure, budget-scoring windows, fund lifecycles,
   and political cycles are shorter than biological and agricultural delays.

Neither hypothesis claims that a better system is technically impossible. Both
concern who captures the gain and when.
