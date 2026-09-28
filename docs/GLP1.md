# GLP-1 treatment experiment

Issue #9 adds an exogenous clinical intervention to the existing health slice.
It is an **uncalibrated software experiment**, not a forecast of prescribing or
a clinical estimate. It does not activate food demand, agriculture, insurance
economics, healthcare spending or policy optimization. Clinical calibration and
the scientific release gate remain open in #1/#27.

## What runs

`scenarios/glp1_access.yaml` starts adoption in year 2, expands access/capacity,
interrupts access in year 9, then restores it in year 12. All prices and coverage
levels in this example are hypothetical scenario assumptions. Treatment affects
only existing metabolic transition hazards; resulting mortality changes pass
through health-state composition and the existing mortality schedule.

The engine tracks the joint distribution of original age cohort, a persistent
indication tag, low/high response group, treatment history and metabolic state.
The five mutually exclusive treatment states are:

- never treated;
- on treatment, response pending;
- on treatment, response present;
- discontinued, response washed out;
- discontinued, residual response present.

These treatment states partition each health stock; they are not additional
people. Death removes people from the corresponding joint cells. The initial
PreChronic cohort uses the same allocation probabilities as the full population,
so a tagged subcohort cannot accidentally receive its own supply allocation.
Original cohorts retain treatment/response history when age cells reach 100+.

Eligibility is distinct from initiation. `glp1_eligible_fraction` initializes a
synthetic indication tag, independently of current metabolic state. Tagged
children cannot initiate until `adult_age`. This is a persistent risk/indication
approximation, **not** measured BMI eligibility or a clinical prescribing rule.
PreChronic and T2D alone do not establish weight-management eligibility.
Contraindications, measured BMI, changing indications, pediatric use and current
prevalent treatment need separate evidence/initialization before calibration.

## Annual allocation and equations

The order is treatment allocation → response/washout → mortality → competing
health transitions → aging. Treatment decisions use health at the start of the
year. All starts are modeled at that boundary; no within-year start-stop cycling
or dose titration is resolved. This deliberately retains the existing annual
health operator. Zero uptake or zero health-effect coefficients reproduce its
baseline, including original-cohort person-time. It does not establish accuracy
at a weekly/monthly clinical timescale.

Each access step explicitly declares availability `A`, coverage fraction `C`,
full monthly price `P`, covered monthly copay `p`, and supply fraction. Copay cannot
exceed full price. Availability and coverage lie in `[0,1]`; prices are nonnegative
USD/month scenario assumptions on a common nominal basis, with no inflation model.
With registered affordability scale `s` in USD/month:

`g = A * (C * exp(-p/s) + (1-C) * exp(-P/s))`.

This uncalibrated acceptance gate averages covered/uncovered access each year;
there is no permanent individual insurance tag or estimated income elasticity.
It is neither an empirical coverage estimate nor a healthcare-cost forecast.

Among previously treated people, requested continuation is
`on * exp(-d) * g`. `d` is the synthetic non-access discontinuation hazard,
with separate T2D/non-T2D inputs. Capacity equals the scenario supply fraction
times the **initial adult population**. Continuers have priority; if requests
exceed capacity they are rationed proportionally, preserving response strata.

First-start demand is `never_eligible_adults * (1-exp(-initiation_rate)) * g`.
Restart demand is `previously_off_eligible_adults * (1-exp(-reinitiation_rate)) * g`.
Both share remaining slots proportionally. Someone stopping in this step cannot
also restart in this step. Residual response survives a restart; washed-out
people restart in the pending phase. Supply/access loss never deletes population.
The report separates underlying-hazard, access and capacity interruptions, plus
unfilled start requests. These are model allocations, not identified clinical
causes of real-world discontinuation.

Pending treated people enter the response phase with probability
`1-exp(-1/glp1_response_lag)` per year. Discontinued people leave their residual
phase with probability `1-exp(-1/glp1_washout_lag)`. These are simple population
phase delays, not an individual concentration or smooth individual weight curve.

Response-group weight reduction is `w = glp1_weight_loss * group_factor` while
in a response phase and zero otherwise. High response has factor one by
definition; the low factor and the mixing share are registered synthetic inputs,
including a possible zero-response limit. Progression hazards multiply by
`exp(-glp1_progression_beta * w)` and recovery hazards by
`exp(glp1_recovery_beta * w)`. Every forward/reverse flow still competes for its
source survivors. The beta units are log hazard per fractional weight reduction.

The separate intake-reduction proxy is reported, but does **not** also change UPF
or independently multiply hazards: doing both would double count an unsupported
mediation pathway. Intake and weight share a response phase in this experiment;
separate appetite/energy-balance physiology is unresolved. There is no direct
mortality benefit, T2D remission, cardiovascular disease module or adverse-event
health burden. Diet and treatment multipliers combine independently, with their
interaction left uncalibrated. Null coefficients are tested explicitly; a benefit
in a synthetic run is a consequence of its sign assumptions, not a finding.

## Evidence and official JSON

The repository stores original NIH/NLM ClinicalTrials.gov API responses:

- [STEP 1 official JSON](https://clinicaltrials.gov/api/v2/studies/NCT03548935)
  ([study](https://clinicaltrials.gov/study/NCT03548935)).
- [STEP 4 official JSON](https://clinicaltrials.gov/api/v2/studies/NCT03548987)
  ([study](https://clinicaltrials.gov/study/NCT03548987)).

These are sponsor-submitted trial records hosted by NIH, not an NIH endorsement
or a national population sample. The pinned records include eligibility,
trial vintage, group definitions and results. The transform selects the primary
weight endpoint by title/type and preserves time origin, observation period,
available-case means/standard deviations/counts and estimand-specific adjusted
differences/confidence intervals separately. A standard deviation is not treated
as a confidence interval. STEP 4 randomized participants after a treatment run-in;
its withdrawal comparison is not a trial of unselected treatment initiators.
The recorded trials exclude diabetes and do not identify effects in Demeter's
T2D stock or an effect common to all GLP-1 regimens.

A separately labeled factual JSON extraction records one-year discontinuation
and restart probabilities with reported 95% intervals from
[Rodriguez et al., JAMA Network Open 2025](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2829779).
The US observational analysis distinguishes T2D/non-T2D groups and uses medication
fills. Restart estimates concern a selected subset with weight measurements,
not all discontinuers. These observations cannot be imported as an independent
non-access hazard while also modeling the access barriers they already include.
No article HTML is presented as official JSON.

All three source files live in `data/sources/glp1/2026-09-28/`, with byte lengths,
SHA-256 receipts, retrieval timestamps, provenance and terms. The small derived
benchmark bundle ships in the Python package and rebuilds offline. Clinical
benchmarks remain `benchmark_only`; engine inputs remain `synthetic` in the
registry with explicit sensitivity distributions. No fit or automatic parameter
replacement occurs. Selecting a drug, regimen, population, observation model,
historical start, uncertainty model and independent holdout is later calibration
work, as is appraising the weight-to-health transition bridge.

## Inspection and verification

```powershell
uv run demeter data rebuild-glp1
uv run demeter evidence glp1 --output outputs/glp1-evidence.json
uv run demeter simulate scenarios/glp1_access.yaml --output outputs/glp1.json
uv run demeter observe scenarios/glp1_access.yaml --draws 4 --samples 8 --destination outputs/glp1-report
Start-Process outputs/glp1-report/index.html
```

Annual output includes treatment stocks, starts/stops/restarts, supply limits,
unfilled requests, treatment person-time/deaths and response-group diagnostics.
Charts read the saved output; trial contrasts have a separate benchmark chart
and are never plotted as engine predictions. Seeded uncertainty samples active
GLP-1 inputs and compares with a paired baseline with treatment and diet changes
removed. The existing global sensitivity analysis includes the active treatment
parameters; its rankings concern the chosen synthetic ranges.

`tests/test_glp1.py` checks analytic initiation/response/washout, joint population
and treated-stock balances, all three health structures, zero-effect and
zero-uptake baselines, adulthood, capacity interruption/restart, response
heterogeneity, price/coverage, provenance, offline rebuilding and corruption.

Design trace: Q-03/RM-04 → the health segment of P-02 plus an explicit exogenous
clinical intervention → I-05/I-07/I-11/I-12 → F-04/F-08 → T-01/T-02/T-05/T-08.
No economic feedback loop is closed. `health/glp1.py` contains the treatment
operators; `model.py` integrates them; `data/glp1.py` preserves source evidence.
