# Dietary response through time

Issue #25 adds testable timing mechanics to the exposure contract. It is an
uncalibrated experiment, not a fitted dietary effect. Existing files use the
original linear single-lag response. `diet_response.kind: dynamic` opts into
independent adjustment and recovery, a fading duration component, and an optional
saturating dose shape. Every added numeric parameter is registered as synthetic,
with a sampling range; scientific mode remains blocked.

## Schedule and annual timing

`scenarios/diet_dynamics.yaml` delays intervention, sustains a lower UPF target,
then returns to the reference. The schedule contains unique increasing
`start_year` values within the horizon. A step applies at the start of that model
year and persists until the next step. Before the first step, relative exposure
is one. A schedule cannot coexist with a static UPF declaration.

```yaml
name: delayed_diet_and_withdrawal
years: 25
mode: validation
health_structure: risk_1
diet_response:
  kind: dynamic
  shape: saturating
upf_schedule:
  - {start_year: 3, value: 0.7, unit: relative_exposure}
  - {start_year: 13, value: 1.0, unit: relative_exposure}
```

Steps also accept `percent_energy` with an explicit `reference_period`; the
example file uses the source-linked absolute form. Reference sex and units must
match. The entire path is checked against the registered software envelope before
simulation, including later steps. Impossible absolute percentages fail even when
extrapolation is requested. Reversal to baseline removes the input deviation;
it does not instantly erase response memory or reset health stocks.

The annual health operator remains mortality → competing metabolic transitions
→ aging. Response values at the end of an annual interval modify its year-end
transition hazards. This is still an annual model; it cannot resolve clinical
changes over weeks. Exact filter subdivision tests do not prove convergence of
the whole annual mortality/transition operator. Charts distinguish the input at
the beginning of an interval from the response at its end.

## Equations and units

Let `u(t)` be relative UPF exposure, `d = u - 1`, and `g(d)` its dose shape:

- Linear: `g(d) = d`.
- Optional saturating alternative: `g(d) = h*d/(h + abs(d))` for positive `h`.

The alternative is continuous, has slope one near zero, and limiting magnitude
`h`. `diet_half_saturation` is a **synthetic shape scale**. No empirical threshold,
clinical saturation, or recommended dose is claimed. Unsupported age-response
modifiers and exposure thresholds are not silently assigned values.

For a constant input over duration `dt`, the exact first-order update is
`L(x,z,tau,dt) = x + (z-x)*(1-exp(-dt/tau))`.

The dynamic response has three states, all initialized to zero deviation:

| State | Update | Role |
| --- | --- | --- |
| Fast response `F` | `L(F,g(d),tau_F,dt)` | `tau_F = diet_improvement_lag_years` when `g(d) < F`; otherwise `diet_lag_years` |
| Retained exposure `M` | `L(M,g(d),diet_memory_years,dt)` | Bounded, exponentially discounted duration history |
| Recovery response `R` | `L(R,-g(d),diet_recovery_lag_years,dt)` | Independent timing for reverse metabolic transitions |

`progression_multiplier = exp(beta_upf_progression * ((1-w)*F + w*M))`, with
`w = diet_memory_weight` in `[0,1]`.

`recovery_multiplier = exp(beta_upf_recovery * R)`.

The convex fast/slow mixture does not count two full dietary effects. At sustained
equilibrium its dose remains `g(d)`. Recovery has a separately registered
coefficient and lag; it is not forced to be the reciprocal of progression.
Lower exposure is beneficial only because these synthetic sign assumptions say
so. Setting both coefficients to zero is an explicit software null experiment.

The progression multiplier modifies H→IR and IR→T2D in the legacy health
structure, or H→PreChronic, PreChronic→prediabetes and prediabetes→T2D in the
four-state structures. Recovery modifies IR→H or PreChronic→H and
prediabetes→PreChronic respectively. Competing exits still conserve people.
**Clinical T2D remission/relapse is not implemented.** Returning someone with a
diabetes history to ordinary healthy/prediabetes states would erase clinically
important history; it needs its own state/observation contract and evidence.

The engine also reports `integral(d dt)` and `integral(abs(d) dt)` in relative
exposure-years. Opposite signed deviations can cancel in the first, not the
second. These are accounting measures, not an inferred irreversible damage dose.
Only the bounded fading-memory state affects hazards. Unknown pre-run individual
diets are not invented: the shared adult response starts from zero, with no
individual history or age-specific response coefficient.

## Historical challenge, including failure

The stored challenge contains eight factual observations from the complete-case
Figure 2 caption of [Gregg et al., JAMA 2012](https://jamanetwork.com/journals/jama/fullarticle/1486829).
It records remission prevalence in both arms over four annual visits, with the
published intervals and counts. An archived [official NIDDK summary](https://www.niddk.nih.gov/news/archive/2013/health-effects-diet-exercise-adults-type-2-diabetes-obesity)
independently corroborates the reported first/fourth-year lifestyle percentages;
it is not an independent clinical dataset. The factual JSON is our labeled
extraction, not publisher JSON. The copyrighted article is not redistributed.
Source receipts and the transform live in `data/sources/diet-dynamics/2026-09-27/`
and `src/demeter/data/diet_response.py`; the derived bundle ships in the wheel.

The observed point contrast declines after the first follow-up. A constant-input
positive first-order response grows monotonically. The diagnostic therefore
normalizes each observed contrast and each response curve by its own first-year
value, and evaluates the existing lag parameter's lower bound, nominal value,
and upper bound. Later points challenge the shortcut that this response can be
used directly as remission prevalence. There is no parameter fitting, optimized
lag, significance test, or transport of a trial effect into the engine.

The shortcut fails on point-trajectory shape for every candidate. **That does
not falsify lag filters embedded inside a stock/flow model.** Remission is an
observed stock prevalence, while our response modifies transition hazards.
The diagnostic also inspects actual engine transitions and exposes the absence
of T2D remission. Changing a lag cannot supply that missing pathway.

The intervention included physical activity and weight-loss support, not isolated
UPF manipulation. Contact intensity, adherence, attrition, relapse and eligibility
can change over time. Repeated-visit covariance is unavailable, so the contrasts
are descriptive; marginal intervals are not treated as independent errors.
The extraction preserves the caption's fourth-year interval as printed and notes
its difference from the main text's imputed analysis. The historical mismatch is
retained as a scientific limitation, not hidden behind a passing software check.

## Uncertainty, sensitivity and observability

Active timing parameters have synthetic uniform ranges, including the existing
`diet_lag_years`. The dynamic response additionally samples improvement, duration
memory and recovery lags, memory weight, recovery amplitude, and the optional
shape scale. Inactive dynamic parameters do not enter legacy uncertainty runs.
Paired baselines clear schedules as well as static targets, retaining the same
response/health structure and identical draws.

`timing-sensitivity` ranks total-order Sobol contributions to final period
healthspan while holding other parameters fixed. This is **conditional sensitivity
under specified synthetic ranges**, not identification of true biological delays.
The ordinary sensitivity report varies all active parameters and also exposes
timing contributions within that larger variance. Rankings depend on dose path,
horizon, health structure and ranges. A constant no-change scenario has no timing
variance and fails explicitly rather than reporting a fictitious ranking.

The dynamic observability report adds five views: input versus delayed hazards,
cumulative exposure accounting, fast/memory/recovery states, timing contributions
within full-parameter sensitivity, and the historical shortcut challenge. All
values come from canonical saved diagnostics. Together with the additional
parameter-distribution charts, the supplied saturating four-state example has
57 views. The existing static reports retain
their chart sets.

```bash
uv run demeter data rebuild-diet-response
uv run demeter diet-lag-challenge --output outputs/diet-lag-challenge.json
uv run demeter simulate scenarios/diet_dynamics.yaml --output outputs/diet-dynamics.json
uv run demeter timing-sensitivity --samples 64 --seed 42 --output outputs/timing-sensitivity.json
uv run demeter observe scenarios/diet_dynamics.yaml --destination outputs/diet-dynamics-report
```

## Design trace and remaining calibration work

Q-03/RM-04 → exposure-to-health part of P-02 → I-05/I-07/I-11/I-12 → F-04/F-08.
The implementation is `nutrition/response.py`, the typed schedule in `schema.py`,
the resolver in `nutrition/exposures.py`, and the explicit forward/reverse hazards
in `health/structure.py`. `tests/test_diet_response.py` covers T-01 units and
conservation, T-02 timing extremes/null effects, T-03 exact filter refinement,
T-05 linear/saturating and response/recovery alternatives, T-06 the historical
challenge, and T-08 uncertainty/pairing/source integrity.

No agriculture, economic or behavior loop is activated. Later calibration must
select a population, exposure, clinical endpoint and observation model together;
appraise dose shape, duration dependence, recovery, age effects and uncertainty;
then test compatible longitudinal holdouts. Those scientific requirements remain
open in #1/#27. Implementing these mechanics is not completion of that gate.
