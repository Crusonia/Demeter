# Related work and positioning

Companion to the [program vision](PROJECT_VISION.md), which summarizes these conclusions. See also the [stakeholder rigidity register](design/06_STAKEHOLDER_RIGIDITIES.md) and the [top-level metrics](PROJECT_VISION.md#top-level-metrics).

Demeter is not the first model of diet and health, nor of agriculture and land use. Mature open and published models already cover individual layers of the system. Demeter's contribution must be stated relative to them.

This survey was compiled in September 2026 from public repositories, papers, and project pages. It records scope, not endorsement. Repository activity, licenses, and code completeness have not been audited; verify them before reusing any code, structure, or output.

## Landscape by layer

| Layer | Existing efforts | Overlap with Demeter | Main gap relative to Demeter |
|---|---|---|---|
| Diet → metabolic state → disease → mortality | **IMPACTncd** (University of Liverpool, R): [core](https://github.com/ChristK/IMPACTncd), [England](https://github.com/ChristK/IMPACTncd_Engl), [Japan](https://github.com/ChristK/IMPACTncd_Japan) | Dynamic individual-level microsimulation of NCD prevention policy with competing risks; obesity, type 2 diabetes, cardiovascular disease, multimorbidity, and mortality; applied to food taxation and labeling | Health and policy only; no agricultural supply, food-company behavior, or value-capture accounting; England and Japan calibrations |
| | **SPHR Obesity and Diabetes Prevention Model v6.2** (University of Sheffield, R): [repository](https://github.com/KPidd/SPHR-Obesity-and-Diabetes-Prevention-Model-Version-6.2); [model description](https://eprints.whiterose.ac.uk/97829/) | Individual metabolic trajectories and diabetes/obesity complications; the earlier SPHR diabetes model was compared with the UKPDS Outcomes Model | Cost-effectiveness scope; English survey population |
| | **DYNAMO-HIA** (Java, GUI): [PLOS One 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3349723/) | Risk-factor states → multiple diseases → life expectancy and disease-free life expectancy from standard epidemiological inputs | Desktop application rather than a composable library |
| | **Proportional multistate life tables** (PRIMEtime, BODE3, University of Melbourne): [concepts and code, IJE 2020](https://academic.oup.com/ije/article/49/5/1624/5920732); [PRIMEtime CE](https://bmchealthservres.biomedcentral.com/articles/10.1186/s12913-019-4237-4) | Established method for translating diet and risk-factor change into disease incidence and health-adjusted life years | Code distributed with papers or spreadsheets rather than as a maintained package |
| | **U.S. food-policy microsimulations** (Tufts and collaborators; e.g. [DOC-M](https://journals.sagepub.com/doi/10.1177/0272989X231196916)); [MONDAC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13131360/) | U.S. diet, obesity, diabetes, and cardiovascular policy outcomes, costs, and disparities | Published results; open code not identified in this survey |
| Microsimulation framework | **Vivarium** (IHME, Python): [framework](https://github.com/ihmeuw/vivarium), [public-health components](https://github.com/ihmeuw/vivarium_public_health) | Python, modular components, GBD-linked disease models, nutrition projects | `vivarium_public_health` is frozen; coupled to IHME data pipelines; no economic actors |
| Diet → health, environment, and cost | **WHO Diet Impact Assessment** (Springmann, GAMS/MIRO): [repository](https://github.com/marco-spr/WHO-DIA) | Dietary scenarios scored for avoidable deaths, environmental footprints, and diet cost | Comparative-risk snapshot rather than dynamic cohorts; GAMS runtime; no actor behavior |
| Agriculture and land use | **MAgPIE** (PIK, GAMS/R): [repository](https://github.com/magpiemodel/magpie); [framework paper](https://doi.org/10.5194/gmd-12-1299-2019) | Food demand, agricultural production, land, water, and emissions under diet scenarios | No health outcomes; food represented as commodities and food energy |
| Global system dynamics | **Earth4All** ([Julia implementation](https://github.com/worlddynamics/Earth4All.jl)) and its derivative FRIDA | Stocks, flows, and feedbacks across wellbeing, food, and energy | Global aggregation too coarse for metabolic epidemiology |

Methodological reviews of the wider field: [microsimulation in food policy](https://pmc.ncbi.nlm.nih.gov/articles/PMC8970827/) and [microsimulation of obesity-related policy](https://doi.org/10.3390/nu18010073).

## Management flight simulators

Interactive system-dynamics simulators already exist for health systems, climate, and supply chains. None found in this survey places food and agriculture inside the simulated system.

| Simulator | Domain | Relevance to Demeter |
|---|---|---|
| **[ReThink Health Dynamics Model](https://rippel.org/dynamics-model/)** (Rippel Foundation; Homer, Hirsch, Sterman, Milstein) | Regional health system: population health, care delivery, equity, productivity, and cost | Closest format analogue. Vensim model with a hosted interface; a free "Anytown" configuration uses U.S. national data. Food enters only as an external driver ([model summary](https://rippel.org/wp-content/uploads/2023/04/ReThink-Health-Model-Summary-v5.pdf)) |
| **[PRISM](https://www.cdc.gov/pcd/issues/2021/20_0225.htm)** (CDC) | U.S. cardiovascular risk factors, mortality, and cost under 32 strategies, including nutrition and weight loss | Public web application with a published validation; a U.S. benchmark for Demeter's health outcomes |
| **[HealthBound](https://systemdynamics.org/healthbound/)** (CDC-supported) | U.S. health reform policy game | Illustrates teaching through resource constraints, delays, and side effects |
| **[En-ROADS](https://www.climateinteractive.org/en-roads/)** (Climate Interactive and MIT Sloan) | Climate and energy policy | Reference design for a fast public simulator; runs in the browser via [SDEverywhere](https://github.com/climateinteractive/SDEverywhere), which compiles Vensim/Stella models and so cannot compile Demeter's Python model directly (see [PROJECT_VISION.md](PROJECT_VISION.md) section 4) |
| **[Beer Distribution Game](https://web.mit.edu/jsterman/www/SDG/beergame.html)** (MIT) | Supply-chain ordering | The original flight simulator; delay-driven amplification relevant to agricultural supply response |
| **[Food Chain Reaction](https://www.cna.org/analyses/2015/food-chain-reaction-global-food-security-game)** (WWF, Center for American Progress, CNA) | Global food-security crisis, 2020–2030 | Facilitated role-play without an underlying simulation model; evidence of decision-maker interest in food-system exercises |

Implications:

- The flight-simulator format is established with health leaders. Demeter's contribution would be the model underneath: food production, prices, and purchasing represented inside the system rather than as exogenous inputs. In short, the target is a ReThink Health–style experience in which food is endogenous.
- Candidate conversations include the Rippel Foundation and the ReThink Health modelers, who hold health-system structure and an established user base, and Climate Interactive, which has deep experience delivering fast public system-dynamics simulators. These are prospective contacts only; no relationship or endorsement exists.
- These simulators earn trust through published structure, calibration, and validation. A Demeter simulator must follow the same order: the interface remains Phase 6 work, downstream of an evidence-backed model.
- An earlier teaching build is acceptable only if it is labeled validation-only and presents no synthetic output as a finding.

## What this implies for Demeter

1. **The Phase 1 health slice is not the differentiator.** Diet → metabolic state → disease → mortality has been implemented and validated several times. Phase 1 is necessary infrastructure and must meet the standards of these models, but public descriptions should not present it as novel.
2. **The unoccupied position is the coupling.** This survey found no open model that connects agricultural production, food prices and product composition, household purchasing, metabolic health, and payer and value-chain accounts in one reproducible system. The market and behavioral layer between agriculture and health, and the accounting of who captures value, are the parts Demeter must build itself.
3. **Borrow methods and validation targets.** Demeter's validation-only healthspan metric uses the Sullivan method ([HEALTHSPAN.md](HEALTHSPAN.md)); proportional multistate life tables are the established reference for comparison and for any later disability-weighted metric such as health-adjusted life years. IMPACTncd and SPHR provide reference designs for metabolic transitions. Reproducing a published result from an established model on a shared scenario is a credible external validation target, especially a U.S. result from the Tufts models. Any borrowed structure or value still enters through the evidence registry with its source, population, and transformations recorded.
4. **Plan for cross-language coupling.** The closest open models use R, GAMS, and Julia. Integration with them will likely happen through exchanged data and harmonized interfaces rather than shared code, and the architecture should allow for that.
5. **Consider collaboration before duplication.** Where an established group owns a validated health engine, collaboration may be more valuable than reimplementation. The IMPACTncd team at the University of Liverpool and the Tufts food-policy modelers are candidate conversations for the health layer; as with the simulator contacts above, no relationship exists. That choice must not compromise Demeter's evidence rules or its independence from any single model's conclusions.

This document describes positioning, not implemented capabilities, and does not change the current phase boundary.
