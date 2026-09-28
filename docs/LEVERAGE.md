# Food leverage and pathway attribution

Issue #26 provides an inspectable answer to **why this model changes** under a
dietary scenario. It does not establish which real-world food policy improves
healthspan. All current food-effect inputs and the new scenario-strength range
remain synthetic; calibration and historical causal validation remain open in
#1/#27.

```powershell
uv run demeter leverage --scenario scenarios/diet_dynamics.yaml --draws 32 --samples 64 --seed 42 --destination outputs/leverage
Start-Process outputs/leverage/index.html
```

The report includes nominal trajectories, absolute/relative endpoint changes,
healthspan and cumulative T2D-entry sensitivity, pathway allocations with
sampling intervals, PreChronic progression/reversal counts, original-population
state time, source/evidence overlays, structural alternatives and historical
observed-versus-predicted benchmark context. HTML, individual Plotly JSON and
canonical `diagnostics.json` are saved together and render offline. The same
analysis is callable through `demeter.analysis.leverage.leverage`.

## Counterfactual and scope

By default the food reference sets relative UPF to one and retains the selected
health structure, dietary response equations, population/mortality vintage,
horizon, sex and GLP-1 policy. `--baseline path.yaml` supplies another dietary
reference. Non-diet assumptions must match. Unlike the broader `uncertainty`
command's no-intervention baseline, this report holds GLP-1 policy in place.
Endogenous treatment composition can still change when health states change.

Only UPF currently has a dietary hazard mapping. Fiber and other context-only or
unresolved exposures are listed as unranked gaps, not assigned invented effects
or zero-effect findings. Absolute source-linked UPF scenarios resolve to the same
relative input contract as ordinary runs. Observed baseline means are held fixed;
survey SEs are not silently repurposed as causal uncertainty.

## What is attributed

The players are the implemented **dietary hazard pathways**, not transition counts
or disease stocks. The legacy response changes two forward hazards in the
three-state engine, or three in a PreChronic engine. The dynamic response also
changes reverse hazards, giving three or five players respectively.

For coalition `S`, run the full model with intervention dietary response on paths
in `S` and reference dietary response on all other paths. Keep the same initial
population, mortality schedule, health transitions, policy and parameter values.
No source stock, baseline hazard, competing exit or mortality flow is removed.
Both dietary response histories are calculated with their own exposure paths.
`simulate(..., dietary_reference=..., dietary_paths=...)` validates this routing
and records the selected paths, reference scenario and routed base hazards in
metadata/annual output. GLP-1 modifiers, when active, apply after dietary routing.

With `n` paths and endpoint value `v(S)`, allocate each path `i`:

`phi_i = sum over S not containing i [|S|! (n-|S|-1)! / n!] * (v(S+i)-v(S))`.

The implementation evaluates every subset, so its allocation is exact for this
game. It averages marginal contributions over all path orders and shares
interactions symmetrically. An inactive modifier is a dummy player with zero
allocation even if its realized flow count changes downstream of another path.
Empty/full coalitions must reproduce the ordinary reference/intervention
endpoints. Contributions must sum to their difference for each outcome and draw.

These are model counterfactuals, not necessarily independently implementable
clinical interventions. Choosing a different reference, grouping paths or changing
the equations can change attribution. Shapley values do not identify natural
direct/indirect causal effects or turn synthetic assumptions into evidence.
See [Ma and Tourani, 2020](https://proceedings.mlr.press/v127/ma20a.html) for
limitations of interpreting Shapley explanations causally; the explicit game
above defines this implementation rather than an observational SHAP estimator.

The primary endpoints are period healthy-state years at birth and cumulative T2D
entries over the scenario horizon. T2D entries are **people**, not prevalence or
an incidence rate with person-time denominator. Negative attribution means a
decrease in the specified outcome. Nominal contributions reconcile exactly up to
floating-point tolerance. Marginal sampling medians and quantile endpoints need
not add, so the report preserves per-draw reconciliation residuals separately.

Transition-count and state-person-time differences are also reported, but are
not summed into a second attribution. A changed reverse-flow count can result
from a changed population at risk even when its dietary modifier is unchanged.

## Global sensitivity and uncertainty

The existing sensitivity command conditions on a fixed food scenario. This
report additionally samples `leverage_upf_scale`, a registered **analysis-only**
coordinate. For each annual relative UPF input:

`sampled_input = reference_input + scale * (intervention_input-reference_input)`.

Zero removes the food contrast, one reproduces the selected intervention, and
larger values amplify it. The registered synthetic range includes zero and is
not an estimated adoption distribution. Both endpoints are checked against the
model's permitted exposure range before sampling. The report never clips or
silently narrows a user's experiment to make it pass. The timing profile remains
fixed. Negative exposure is invalid even if extrapolation is explicitly allowed.

Ordinary simulation dependency metadata and scientific input checks audit only
the chosen scenario's active model parameters. The analysis-only coordinate and
inactive optional mechanisms do not become health dependencies. The full evidence
audit still lists every registered parameter, and the registry hash and explicit
scientific-release blockers retain their full scope.

Independent registered uniform draws cover all active uncertain model parameters
and the scenario coordinate. Fixed parameters remain fixed. One draw is reused
for both endpoints and every coalition. Central 95% sampling intervals describe
these declared parameter/scenario ranges, not empirical confidence or all
structural uncertainty. Draws and seeds are saved. Small runs are smoke tests;
more samples do not repair missing causal evidence or omitted covariance.

The [SALib Sobol implementation](https://salib.readthedocs.io/en/latest/api/SALib.analyze.html)
provides first- and total-order indices with bootstrap half-widths. One shared
Sobol design evaluates both endpoints and both outcomes. For each outcome the
report separates:

- variance of the intervention's final level;
- variance of the intervention-minus-reference change.

This prevents a driver of baseline disease from being silently described as a
driver of dietary benefit. Total-order indices include interactions and need not
sum to one. Negative/noisy estimates and bootstrap widths remain visible. A
constant contrast has undefined sensitivity indices, represented explicitly as
`zero_variance` with no fictitious ranking. Undefined bootstrap statistics are
null rather than nonstandard JSON NaNs. No grade-weighted causal score is invented.

## Evidence and structural limitations

Every ranked input carries its registry status, grade, units, source link,
distribution and role. The report lists weak/synthetic inputs in contribution-to-
contrast-variance order. An important but weakly evidenced parameter is a research
priority under that experiment, not a confirmed real-world lever. Evidence grades
are metadata and never multiply effect sizes or variance contributions.

The structural panel compares a null dietary effect, the alternative linear or
saturating dose shape when dynamic response is active, and the other candidate
PreChronic initialization when applicable. These are separate named experiments,
not an ensemble with invented probabilities. Missing exposures, correlated
uncertainty, clinical transport, remission and age-dependent mechanisms cannot
be ranked using variance of the implemented model and remain explicit gaps.

The current food path reaches healthspan through health-state transitions, then
healthy-state weighting and state-sensitive mortality. There is no direct
food-to-mortality modifier. Its implemented contribution is structurally zero;
its empirical effect is **unknown**, not estimated zero. The report does not
claim separately identified natural mediation through morbidity versus mortality.

Historical charts use the existing source-linked persistence/trend forecasts and
holdout boundaries. They provide observed-versus-predicted **context**. They do
not retrospectively validate the dietary engine or its attributed effects, and
no parameters are fitted by the leverage command. No new dataset is introduced;
the existing repository source stores and reload commands remain authoritative.

## Implementation and validation trace

Q-03/RM-04 → health segment of P-02 → I-05/I-07/I-11/I-12 → F-04/F-08 →
T-01/T-02/T-05/T-06(context only)/T-08. No new economic feedback is activated.

- `health/structure.py` identifies dietary-modified paths.
- `model.py` routes reference/intervention modifiers while preserving the engine.
- `analysis/leverage.py` evaluates the game, shared draws, sensitivity and gaps.
- `analysis/leverage_visualization.py` only renders saved output.
- `tests/test_leverage.py` checks analytic Shapley interactions/dummy players,
  known linear Sobol indices, endpoint equivalence in all health structures,
  conservation, GLP-1 policy invariance, exposure bounds, reproducibility, null
  contrasts, clinical-evidence separation and canonical rendering.

The scientific milestone remains incomplete until effects, population mappings,
uncertainty and historical predictions have been calibrated and independently
validated. The engineering report makes those dependencies inspectable now.
