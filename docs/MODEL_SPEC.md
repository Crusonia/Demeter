# Model specification — 0.1.0a1

The separate [paired remission observation analysis](PAIRED_REMISSION_OBSERVATIONS.md)
constrains source labels across visits and retains unknown follow-up categories.
It is outside the annual simulation operator described here. It does not add a
clinical remission state, fit hazards, erase diagnosed history or alter health
equations/active parameters. Clinical state and observation mapping remain unresolved.

## Stocks, units, and sequence

`N[a,s]` is a count of people at age `a` in state `s`: healthy/normoglycemic, insulin-resistant/prediabetes proxy, or type 2 diabetes. Ages are 0–99 and the open group 100+. A scenario selects total, male, or female source data. Sex-specific simulations use the same synthetic metabolic assumptions; they do not estimate sex-specific metabolic effects.

Census resident counts initialize each age. A registered synthetic adult age and three synthetic adult shares allocate counts to states; younger ages start in the healthy state. This allocation is not a calibrated description of U.S. health. Each annual step applies exposure lag, mortality, transitions among survivors, then aging. Births and net migration are explicitly zero. The 100+ group retains its survivors and receives age-99 survivors.

Population identity at every step:

`initial population = surviving population + cumulative deaths`.

## Mortality calibration

From NCHS obtain annual `q[a]`, the probability of dying in the age interval. State hazard multipliers are `r[s]` with healthy fixed to 1. Solve for a baseline hazard `h[a]` such that:

`sum_s reference_share[a,s] × (1 − exp(−h[a] × r[s])) = source_q[a]`.

This calibration uses the initial state shares. Freeze the resulting state-specific hazards throughout a scenario; recalibrating to each year's changing shares would erase the state-to-mortality mechanism. Annual deaths equal each stock times its state-specific death probability. Clinical hazard ratios are still synthetic. Reproducing aggregate mortality does not validate their decomposition.

Calibration now verifies the reconstructed probabilities instead of assuming
that a fixed base-hazard search bracket covers every positive state ratio. The
established ordinary-case arithmetic remains unchanged. Where it misses a
target, a normalized hazard coordinate and adaptive bracket avoid loss of root
precision at small or large ratio scales. Positive targets are checked with
relative error only; a zero target requires exactly zero state hazards. The
verification bound is `4096 × float64 epsilon` (about `9.09e-13` relative), a
computational bound preserving the existing solver's measured roundoff, not a
clinical calibration or acceptance tolerance. Closed-interval probabilities
must be below one; a probability of one cannot identify a finite hazard.
Incomplete/invalid partitions or nonrepresentable state hazards fail explicitly;
weights, ages and source values are not repaired to make calibration pass.

The terminal source group has `q100 = 1` over its entire remaining lifetime; that is not an annual probability. For simulation, calibrate exponential state hazards so the frozen-state mean remaining lifetime matches source `e100`: `h100_base = sum_s(reference_share100[s]/r[s]) / source_e100`. Annual death probabilities are then `1 − exp(−h100_base × r[s])`. Period terminal years use `sum_s(current_share100[s]/h100[s])`. This tail holds states fixed; it does not model transitions within the tail.

The terminal calculation retains its ordinary arithmetic and verifies the
reconstructed remaining years. A fallback combines binary exponents before
summing the nonnegative terms `reference_share[j] × r[s] / (r[j] × source_e100)`;
this prevents an intermediate reciprocal overflow from destroying a finite
answer. Returned state hazards must remain finite and positive in the tail.
The computation still conditions on the supplied state shares and ratios; it
does not identify either from the aggregate life table.

## Metabolic flows

For healthy survivors, annual progression probability is `1 − exp(−lambda_HIR)`. For IR survivors, two competing hazards `lambda_IRH` and `lambda_IRD` give exit probability `1 − exp(−(lambda_IRH + lambda_IRD))`; divide exits in proportion to the two hazards. No survivor can exit twice. No T2D remission pathway is assumed. Pediatric progression is omitted.

Unlike the former scaffold's bounded fractions, registered transition units are now **hazard per year**. Hazard values are nonnegative and may exceed 1; the exponential conversion guarantees valid probabilities.

Finite competing hazards are partitioned without overflowing their sum or losing
representable flows through an intermediate product of survivors and a hazard.
Division precedes multiplication if that intermediate product would overflow
or enter the subnormal range. When necessary, the calculation
uses hazards divided by their maximum to retain the relative exit proportions.
If a relative hazard is too small for a normal floating-point fraction, binary
mantissas and exponents combine the stock and hazard before rescaling, retaining
a representable flow even when the fraction alone would round to zero.
For a hazard sum beyond floating-point range, `exp(-sum)` is already represented
as zero, so all source survivors exit in those proportions. This is numerical
evaluation of the same annual equation, not an empirical hazard cap. Safe
ordinary-case arithmetic is preserved. The shared kernels also serve original
cohort accounting and GLP-1 health transitions; mortality ordering, adult
eligibility and the rule of one endpoint transition per year remain unchanged.

## Diet and lag

UPF can be specified as a relative exposure or an absolute percent-energy target
with a named observed reference. Absolute targets normalize as `target/reference_mean`.
The [food-exposure contract](FOOD_EXPOSURES.md) preserves units, reference sampling
uncertainty, source population and scenario assumptions. Observed nutrient targets
require `context_only`; no independent health effect is inferred. Legacy fiber and
fruit/vegetable multipliers may remain at 1 but changes are rejected.

Target log multiplier is `beta_UPF × (relative_exposure − 1)`. Each year the applied log multiplier approaches this target by fraction `1 − exp(−1/lag_years)`. Its exponential multiplies both H→IR and IR→T2D hazards in this synthetic experiment. The two-path mapping is unresolved and must be revisited when direct endpoint evidence is encoded.

The accepted range is a registered software validation envelope, not an empirical study range. Values outside it require explicit `allow_extrapolation: true`; the result reports extrapolation. That flag does not permit scientific mode. The model does not automatically interpret observational associations as causal effects.

An optional [dynamic response](DIET_DYNAMICS.md) adds piecewise-constant schedules,
asymmetric input adjustment, convex fading exposure memory, independent reverse
transition response and an optional saturating dose shape. All added coefficients
and timing distributions are synthetic registry entries. It retains annual
mortality/transition/aging order and existing health stocks; T2D remains absorbing.
Original single-lag behavior is the default. Timing sensitivity and a historical
observation-shortcut challenge are separate from parameter calibration.

## Life tables and healthy state years

For each age, mix state death probabilities using current state shares. Empty age cells use reference shares; this is disclosed in each annual row. This provides a complete period schedule even after younger cells empty in a closed population.

The independent life-table calculator computes:

- `d_x = l_x q_x`
- `L_x = n l_x − (n − a_x)d_x` for closed intervals
- `L_100 = l_100 e_100` for the open interval
- `T_x = sum_{i >= x} L_i`
- `e_x = T_x/l_x` when survivorship is positive

Source `a_x` is derived from published `L_x`, `l_x`, and `d_x`; it is held fixed under scenario changes. The calculator is tested against synthetic arithmetic and published NCHS `e_x` at all ages, not merely rounded life expectancy at birth.

The primary `healthspan` metric uses `sum_x(L_x × healthy_share_x)/l_0`, retaining
`metabolically_healthy_life_expectancy` as an alias. This Sullivan calculation
also reports conditional remaining years by age and state. Separately, original
cohort time integrates constant within-year mortality before year-end transitions,
with no extrapolation beyond the simulation horizon. Neither metric includes all
disabilities or diseases. [HEALTHSPAN.md](HEALTHSPAN.md) defines the equations,
competing risks, unavailable measures, uncertainty, and the published NCHS
arithmetic benchmark. Sourced disability weights can use the same person-year
interface without redefining mortality, once joint-condition semantics are specified.

## Uncertainty and comparison

Monte Carlo samples the registry's declared distributions with an explicit NumPy seed. Baseline and intervention use the same sampled parameter set for each draw. Reports include medians and central 95% parameter-sampling intervals for scenario outcomes and paired deltas. Published confidence intervals without a specified distribution cannot be sampled silently. Current varying distributions are synthetic independent uniforms; initial state shares and source inputs are held fixed.

SALib Sobol estimates first-order and total-order variance contributions and confidence half-widths. It currently requires independent uniforms. The sample count must be a power of two. Zero output variance fails explicitly.

Paired no-change baselines clear both relative and absolute dietary changes.
Observed dietary reference means are held fixed: their sampling SEs and intake
distributions are retained in metadata, not converted into causal parameter draws.

Comparison requires the same horizon, sex, source year, and execution mode. Outputs include absolute and relative differences, full scenario definitions, model version, evidence hash, source bundle hash, vintages, synthetic flags, and limitations.

## Validation boundary

Optional `risk_1` and `risk_2` health structures add a separate PreChronic stock,
reversible transitions and tagged initial-cohort T2D accounting. Their equations,
synthetic parameters, observation definitions, uncertainty and limits are in
[PRECHRONIC.md](PRECHRONIC.md). The default three-state equations above remain
available as `legacy`; none of the new survey data silently replaces engine inputs.

Mortality reconstruction tolerance is 0.001 years at every age. Conservation tolerance is a small numerical residual, not a statistical fit. The historical persistence benchmark uses the 2022 schedule to predict 2023 without using holdout mortality in the prediction. Prevalence checks expose discrepancies and definition mismatches instead of counting synthetic shares as a successful calibration. Scientific mode is disabled in this alpha even if evidence labels are edited.

## Instrumentation

An explicit [transition-module argument](MODULE_API.md) can replace annual base
health hazards through a versioned contract. The engine still owns mortality,
competing flows, aging, adult eligibility and tagged-cohort accounting. Extra
module dependencies are validated and included in evidence metadata; unused
canonical hazard keys are excluded for replacement modules. Default runs retain
their existing equations. Custom results record the module's source fingerprint,
contract and annual hazards and remain experimental/validation-only.

The [food-leverage analysis](LEVERAGE.md) can route reference versus intervention
dietary modifiers separately to each existing transition. Baseline hazards,
competing flows, mortality and non-diet assumptions remain intact. Its exact
Shapley allocation explains the resulting model contrast; it is not identified
biological mediation. A registered analysis-only UPF contrast coordinate adds
exposure variation to paired global sensitivity without becoming a model hazard
coefficient. Ordinary simulation behavior is unchanged when routing is absent.

An optional [GLP-1 treatment experiment](GLP1.md) augments health stocks with
persistent indication, response group and treatment-history strata. Its annual
treatment allocation and response/washout operator precedes mortality and the
existing competing metabolic transitions. Treatment changes those transition
hazards through an explicitly synthetic weight-response bridge; intake is a
diagnostic proxy. No direct mortality or T2D-remission effect is added. Paired
uncertainty baselines clear treatment as well as dietary changes.

`simulate(..., diagnostics=True)` additionally emits annual age-cell stocks,
state-specific death counts, the exact period life tables and the implemented
transition/dependency structure with evidence metadata. The optional recording
path does not change equations or the order of operations. In the open 100+ group,
`annual_death_probability` is the mixed one-year mortality probability, while
life-table `qx` is 1 over the full remaining open interval. These must not be
interchanged in plots. Parameter uncertainty can record annual quantiles and
actual sampled inputs. Renderers consume these outputs without recomputing model
logic; see `OBSERVABILITY.md`.
