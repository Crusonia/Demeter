# RFC-57: Evaluate linked longitudinal observations before fitting clinical rates

Status: proposed software contract; October 1, 2026 UTC. Supports
[#57](https://github.com/Crusonia/Demeter/issues/57),
[#58](https://github.com/Crusonia/Demeter/issues/58),
[#1](https://github.com/Crusonia/Demeter/issues/1) and
[#27](https://github.com/Crusonia/Demeter/issues/27). No empirical fit, clinical
parameter promotion or engine activation is authorized by this RFC. Independent
human scientific review remains pending.

## Decision and current gap

Implement a Python library evaluator for a complete, explicitly declared
longitudinal observation path. Preserve dependence between visits, diagnosis
history, treatment segments, competing death and event stopping. Add local
observable-identification diagnostics. This implements part of F-08 rather than
another marginal source benchmark.

The [DPP adapter](../DPP_OBSERVATION_ADAPTER.md) preserves normalized observations
but supplies no clinical likelihood. The [Whitehall endpoint](../WHITEHALL_ENDPOINT.md)
fits a conditional endpoint-label probability. The
[DiRECT paired observations](../PAIRED_REMISSION_OBSERVATIONS.md) constrain feasible
joint source-label counts without a sampling likelihood or observed death/loss
partition. None supplies the repeated clinical observations and source contract
needed to identify the full requested hazards.

The [protocol](../validation/longitudinal-likelihood-protocol-v1.json) freezes the
software equations, arbitrary fixture inputs, observation definitions, diagnostics
and failure dispositions before any evaluation of this new fixture. It contains
no participant observations, source-effect extraction or clinical values. Synthetic
inputs and numerical controls must be registered before execution. Software
verification is not empirical calibration, preregistration of a clinical study,
independent prediction or scientific release acceptance.

Design chain: health portion of Q-03/RM-04 -> P-02 -> I-01/I-07/I-11/I-12 -> F-08 ->
T-01/T-02/T-05/T-06/T-08 in the [design registers](../design/README.md). F-04 still
requires a separately identified dietary exposure, effect, dose and lag. This work
activates no business externality, economic feedback or later-phase module.

## Separation from the annual engine

The current engine applies mortality, then one transition among surviving stocks,
then aging. It includes no T2D remission flow. A continuous-time generator permits
intermediate transitions within an interval; in general `exp(Q * t)` is not the
implemented annual operator. No equality, annual rate replacement or source-to-engine
bridge is assumed here. The existing [clinical observation contract](../CLINICAL_OBSERVATION_CONTRACT.md)
and [identification RFC](RFC-57-longitudinal-identification.md) remain authoritative.

The proposed core API uses `StateSpace(labels, diagnosis_history, death_index)`,
`RateSegment(start_year, end_year, generator)`,
`PanelObservation(time_year, emission, kind)` and
`TerminalObservation(kind, time_year, event, interval_start_year, endpoint_emission)`.
`SoftwareObservationContract` requires six known declarations: time unit,
observation timing, missingness, selection, treatment and stopping. The shared
`path_likelihood` evaluates a supported panel prefix and its declared terminal mode.
Category and coarsened panel kinds are explicit; this is not a participant importer.
The core receives emission vectors, not raw diagnosis/history fields. A caller
constructs the documented toy masks; contradictory history then has no compatible
path and contributes exactly zero, rather than being renamed recovery or repaired.

The library requires explicit state-space and observation definitions. It must not
silently equate a glucose category with metabolically healthy, insulin resistant,
T2D, biological onset or untreated remission. A recorded diagnosis and its timing
are different observations from a physiological transition.

## Declared synthetic state space

The validation fixture uses five arbitrary states, not validated engine states:

| Label | Software meaning | Diagnosis-history attribute | Toy glycemic label |
| --- | --- | --- | --- |
| N | No diagnosed-T2D history; lower glycemic label | No | Lower |
| P | No diagnosed-T2D history; higher glycemic label | No | Higher |
| D | Diagnosed-T2D history; higher glycemic label | Yes | Higher |
| R | Improved glycemic label with diagnosed-T2D history retained | Yes | Lower |
| death | Separate absorbing death destination | Not newly classified | Death |

These labels have no assay thresholds, clinical tolerance or national applicability.
In particular, R does not mean that prior diagnosed T2D disappeared or that a
treatment-free persistence criterion was met. Allowed transitions never erase a
known diagnosis history; death has no outgoing transition.

The fixture has declared off-diagonal rates in reciprocal years and entry P.
Segment A applies from the origin to year 1; segment B applies from year 1 to year
3 and changes only P -> N. The arbitrary change is a piecewise treatment/regime
software exercise, not an estimated treatment or dietary effect. Every numeric
input is listed with its registry key in the protocol. Diagonals are the negative
sum of all outgoing rates, including competing death.

## Observation and path likelihood

For row-vector entry weights `alpha`, a categorical observation y contributes its
declared diagonal emission operator `E_y`. A set-valued observation contributes the
sum of operators for its explicitly observed alternatives. The fixture uses
deterministic toy category membership; the library must not invent or fit
measurement-error probabilities.

Between observations, propagate with the chronological product of
`exp(Q_segment * elapsed_time)`, splitting at every declared regime boundary.
Update with the observation operator and a compatible diagnosis-history mask.
The whole-path probability is the resulting row vector summed over compatible
terminal states. Evaluate with scaling/log accumulation for numerical stability;
do not multiply independently fitted marginal visit probabilities.

The main path has an explicitly set-valued living category observation without
diagnosis history at year 0.5, a higher category with diagnosis history at year 1.5,
then a lower category at year 3. The last history field is not assessed: the earlier
positive history persists. These fixed toy visits are declared exogenous. Their
categories and history masks are observations; they do not locate the first
diagnosis at an exact biological transition time.

Unknown is not a negative test, no diagnosis, no death or an emission of all ones.
A set-valued observation is supported information, distinct from a missing test.
An explicit coarsening/measurement contract may authorize compatible-state
marginalization; otherwise a dependent likelihood mode is blocked. The initial
scope does not model informative visit scheduling, treatment assignment or
informative loss. Known treatment segments are conditioned on, not given a causal
interpretation. A source with unresolved versions, units, confirmation, history,
selection or stopping cannot become fit-eligible through this software contract.

## First-entry event and competing death

A separate fixture declares that the event equals first entry to D and that death
competes with it. This equality is a synthetic assumption only. Before either
terminal event, the reachable transient states are N and P. Their killed
subgenerator A retains the original negative diagonals, including hazards out to
both D and death. Removing the event destinations must not remove those hazards
from the diagonals.

For a homogeneous interval with event vector `r_D`, exact first-event density is
`alpha * exp(A * t) * r_D`. An interval observation integrates that density over its
declared bounds; right censoring contributes the probability of remaining event-free
and alive through its supported follow-up time. Death uses a separate `r_death`.
Event densities have reciprocal-time units and need not be bounded by one;
probabilities are dimensionless. Unknown status cannot be treated as survival.

Piecewise event calculations split at the same declared regime boundaries as the
panel model, including inside an event interval. Integrals must account for
survival into each segment; no average rate, interval midpoint or common annual
probability is substituted. Use an augmented matrix exponential or another
independently verified stable integral, including zero/singular-generator cases.

If a supported earlier panel observation is included in a first-entry path,
propagate its event-free prefix with the killed kernel and the actual observation
operator before the terminal event contribution. The initial API may reject
additional observations inside a terminal event interval; it must not drop them
or replace them with a last-negative shortcut. A last negative glucose test and
known no-diagnosis history constrain different events. Exact death after a full
living-state panel uses `exact_first_entry` with event/target death only, so the
transient process retains both no-history and diagnosed-history living states.
It contributes a death density, not a terminal-death occupancy probability.
An event-free measured endpoint uses the killed kernel and endpoint emission
jointly; it is normalized by survival only when an explicit conditioning contract
requires that distinct estimand.

Last glucose, last known alive contact, last event ascertainment and administrative
end are distinct. Censoring requires the declared ascertainment/stopping clock.
Unknown clocks, cross-unit ordering, unknown competing-death status or unjustified
censoring assumptions block the dependent calculation. Confirmation dates cannot
be converted to first entry without a separate source model.

The primary [msm methodological manual](https://cran.r-project.org/web/packages/msm/vignettes/msm-manual.pdf),
sections 1.3-1.4, distinguishes intermittent-state probabilities, exact-death
densities and censored-state contributions, and states the need to assess the
observation process. It supports these computational distinctions, not the toy
clinical state definitions or their empirical adequacy.

## Local identification diagnostics

The full toy observation design consists of all four living entry-state rows and
all five terminal-state probabilities at year 3 under homogeneous segment A.
Numerically differentiate those observable probabilities with respect to the nine
base off-diagonal rates. Report the Jacobian, singular values, dimensions and local
rank with the registered finite-difference step and numerical threshold. The
registered relative threshold multiplies the largest singular value; a zero
Jacobian has rank zero. Report both the relative setting and effective absolute
cutoff. The full-rank hypothesis is an unexecuted software test,
not an empirical finding.

A second design observes only P entry and terminal lower-label probability, the
sum of N and R terminal masses, at that same horizon. Its scalar observable has
rank at most one against the same nine free rates. These are different declared
experiments; the full design is not a claim that current sources expose all rows.
Segment B's separate rate is fixed, outside this homogeneous nine-rate diagnostic.
No parameter is silently fixed to make actual source data look identified.

A closed-form counterexample uses a separately restricted N <-> P toy model with
all other edges zero. Starting in P, its terminal N probability is
`q = b / (a + b) * [-expm1(-(a + b) * t)]`. Use registered base a and b, and define
an alternative total `s2 = base_a + segment_B_b`. Then
`b2 = q * s2 / [-expm1(-s2 * t)]` and `a2 = s2 - b2` give the same scalar endpoint.
Compare its full transition rows as well. This demonstrates indistinguishable
scalar endpoints in that restricted toy; it does not reproduce the five-state
fixture, a published Cox model or a clinical cohort.

Local numerical rank does not prove global, practical, latent-state or causal
identification. Conditioning on selected survivors, treatment or measured visits
does not establish an intervention effect. Measurement-error parameters require
their own evidence and identifiability analysis. No optimizer, clinical fit,
sampling interval or joint clinical covariance is added in this change.

## Proof and failure dispositions

Verify whole-path evaluation against enumeration of compatible short state paths;
categorical partition and set-valued sums; probability conservation, absorbing
death and retained history; chronological segmentation; exact-event density and
interval/censoring identities; zero-event and impossible-observation boundaries;
and local full/scalar rank diagnostics with the explicit alternative above.

Test strict units/types, duplicate observation times, impossible contradictory history, unsupported
missingness and event stopping, and input mutation isolation. Numerical tolerances
are software roundoff/finite-difference controls, never clinical acceptance cutoffs.
Small negative matrix-exponential entries may receive a disclosed numerical
roundoff correction only within the supplied tolerance. Do not repair a generator,
negative input rate, substantive probability violation or impossible path. No
positive likelihood floor is permitted. Do not force a failed identity or rank
test to pass by clipping or changing the frozen fixture. Retain the failure and
use a reviewed versioned amendment if needed.

| Disposition | Meaning |
| --- | --- |
| Computational evaluation | Declared inputs have a mathematically valid contribution; not a source or clinical endorsement |
| Software verification | Frozen synthetic identities/guards pass; outputs remain validation-only |
| Source eligibility | Separate clinical source contract and immutable permitted evidence are required; current packages remain blocked for full clinical fitting |
| Clinical identification/fit | Requires compatible observations, identifiable parameters, joint uncertainty and an estimation/evaluation protocol; not performed here |
| Independent prediction | Requires untouched supported observations and frozen metrics/tolerances; not performed here |
| Engine activation/scientific release | Requires compatible engine semantics, transport, canonical before/after verification and scientific review; not authorized here |

Chen timing/version gaps, DPP documentation-only access, Reus first-event effect
ambiguity, PREVIEW selected endpoint/missingness, TOTUM unverified clinical row
adequacy, Whitehall conditional terminal labels and DiRECT composite-failure
partitions remain unresolved for the full requested clinical dynamics. Their
restricted supported outputs remain valid within their own contracts. This is
not an exhaustive claim that public longitudinal evidence is unavailable.

Root integration should preserve active parameter definitions and canonical
numerical outputs, emit aggregate synthetic diagnostics with protocol/registry/code
provenance, and retain `validate --scientific-required` failure. No raw participant
paths or identifiers belong in the public report. Passing this PR does not close
#57/#58/#1/#27.
