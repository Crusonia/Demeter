# Linked observations and event timing

Demeter now has a separate Python evaluator for linked visit observations and
first-entry events under explicitly declared assumptions. It is a software
exercise with synthetic inputs, not a clinical fit. The annual simulation engine
and its parameters are unchanged.

After the [normal setup](GETTING_STARTED.md), run from the repository root on
Windows PowerShell, macOS or Linux:

```bash
uv run demeter evidence longitudinal-likelihood --output outputs/longitudinal-likelihood.json
```

The command runs the fixed registered fixture offline. It does not read participant
records, download data, estimate hazards or change a scenario. The output must be
a new filename; use a different name for another saved run. Omit `--output` to read
the report in the terminal. A failed frozen-input check or numerical identity
exits nonzero and cannot promote clinical eligibility.

## What the exercise teaches

Repeated visits are one linked path. A person observed in a higher glucose category
and later a lower category can retain a prior diabetes diagnosis. Their observations
do not automatically mean untreated remission or reveal the first biological onset
time. The toy states therefore retain diagnosis history; they have no clinical
thresholds or national interpretation.

| Contribution | What was explicitly observed | Units |
| --- | --- | --- |
| Linked panel | Categories or declared category sets at linked visit times | Probability |
| Exact first entry | A declared event at an exact relative-year time | Density per year |
| Interval first entry | A declared first event within supported bounds | Probability |
| Right censoring | Event-free and alive through an explicitly supported clock | Probability |
| Non-event endpoint | An observed compatible endpoint without any competing first event | Joint probability |

Death is a distinct competing destination. A missing glucose assessment is not
survival, a negative result or death. Stopping after diagnosis differs from a fixed
visit schedule. The library rejects unknown required assumptions and observations
inside a terminal event interval it cannot represent. A panel end alone does not
assert that the person is alive.

Known regime changes split propagation into chronological segments. Exact event
density at an internal segment boundary uses the right-hand regime; at the final
schedule end it uses the last regime's left limit. An exact density and terminal
death occupancy are different quantities. The fixture's event equals first entry
to a toy state by assumption; no clinical detection/onset equivalence is inferred.

The report compares scaled forward evaluation with explicit path enumeration and
checks competing-event/death/survival mass. A simple competing-hazard example also
has an independent analytic and quadrature check. All rates, times and diagnostic
settings are synthetic grade E, registered in `evidence/parameters.yaml` and kept
`benchmark_only`.

The full toy observation design can locally distinguish its named rates at the
chosen point. A single endpoint probability cannot distinguish nine rates. The
report retains a closed-form alternative in a separately restricted two-state toy
that has the same scalar endpoint but different full transition rows. Numerical
Jacobian rank depends on observable design, units, step and tolerance; it does not
prove global, practical or causal identification, or identify clinical rates.

## Design and evidence gates

The [RFC](rfcs/RFC-57-longitudinal-likelihood.md) and
[frozen protocol](validation/longitudinal-likelihood-protocol-v1.json) were committed
with all 19 registered numeric inputs in `9cee09e` before the new numerical checks.
The implementation verifies their byte hashes and exact parameter roles/values
before calculation. Numerical roundoff corrections apply only to small negative
matrix-exponential entries within the declared tolerance; input hazards and failed
identities are never repaired to force a pass.

The [reproducible report](validation/issue-57-58-longitudinal-likelihood.json)
records protocol, registry and code hashes. The
[before/after proof](validation/issue-57-58-longitudinal-likelihood-before-after.json)
checks that prior evidence records, active parameters and canonical numerical
outputs remain unchanged. Research design trace:
Q-03/RM-04 → P-02 → I-01/I-07/I-11/I-12 → F-08 → T-01/T-02/T-05/T-06/T-08.

Clinical fitting still requires a permitted, pinned source with compatible linked
observations or sufficient joint aggregates, measured timing/history/treatment,
death/loss/assessment coverage, a justified observation/selection model, identifiable
parameters, joint uncertainty and independent evaluation. A declared software flag
does not verify any of these facts. Current Chen, DPP, Reus, PREVIEW, TOTUM,
Whitehall and DiRECT packages keep their existing clinical limitations.

This capability does not close issues #57, #58, #1 or #27. Dietary effect, dose and
lag, U.S. transport, health calibration and independent prediction remain open.
The continuous-time evaluator is separate from the current annual mortality-then-
survivor-transition engine. No agriculture, business-value or healthcare-savings
conclusion follows from this exercise. The broader phased program remains in the
[project vision](PROJECT_VISION.md).

## Numerical correction and current-code replay

The [preserved v2 amendment](validation/longitudinal-probability-contract-amendment-v2.json)
corrects the former ability to admit impossible mass by supplying a loose caller
tolerance. The original protocol and results remain unchanged. Stochastic checks
now accept an allowance at most `1e-10`, the existing registered software ceiling;
the local Jacobian's relative rank cutoff remains a separate design choice.
Generator conservation is checked after dividing each full row by its largest
absolute hazard. This dimensionless check detects relative errors even in tiny
rates without changing any input rate. Diagnostics retain the initial mass
deviation and each scaled generator row sum.

Accepted roundoff deviations are not repaired. Working forward scaling retains
the original initial mass in the likelihood and normalizers, including at a
zero-time terminal. A non-density contribution whose computed log probability is
positive, or whose displayed probability exceeds one, fails explicitly. Exact
first-entry densities may exceed one because their units are per year. This
strict policy can reject a mathematically valid all-state observation when
matrix-exponential or forward arithmetic produces slight surplus mass. Such a
failure is numerical, not structural impossibility or a scientific result; the
library neither clamps the probability nor increases the tolerance to pass it.

The [current v3 amendment](validation/longitudinal-probability-contract-amendment-v3.json)
also rejects nonfinite exact-event aggregate hazards, density factors, nonzero-path
log likelihoods and displayed contributions. Finite input edges can overflow when
summed near the binary64 ceiling; this fails explicitly rather than returning an
infinite fitted contribution. Finite densities above one and structural zeros keep
their existing meaning. Independent review found this defect in published revision
`af223600843b8ea40ae9c51a2f87a3a1061a903d`; its failed case and the original
[v2 replay](validation/longitudinal-probability-contract-replay-v2.json) remain
historical records of that earlier code. Neither prior artifact is rewritten to
claim the extreme input passed.

The [current-code replay](validation/longitudinal-probability-contract-replay-v3.json)
uses the original 19 registered inputs and compares the old mathematical outputs
under unchanged tolerances. Run its verifier from the repository root:

```bash
uv run python scripts/verify_longitudinal_probability_contract.py
```

Focused tests exhaust token paths for small complete synthetic channels and
compare CTMC panel contributions with the nominal evaluator and hidden-path
enumeration. This equality requires caller-known synthetic times and matching
joint observation definitions. It does not turn source visit labels into years,
identify a CTMC generator for every nominal matrix, or equate panel probabilities
with first-entry densities or the annual engine. The amendment follows defect
inspection and initial corrective tests; it is not prospective registration or
independent validation. No empirical input or scientific gate changes.
