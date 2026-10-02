# RFC-57: iPOP recorded-A1C dynamics

Status: proposed scientific interpretation; October 1, 2026. This implements a
source-specific empirical working analysis toward [#57](https://github.com/Crusonia/Demeter/issues/57).
It does not complete clinical progression/reversal calibration or activate engine
rates. External scientific assessment remains pending.

The design chain is Q-03/RM-04 -> P-02 -> I-01/I-07/I-11/I-12 -> F-04/F-08 ->
T-01/T-05/T-06/T-08, with L-00 bookkeeping only. The
[program vision](../PROJECT_VISION.md) and [clinical contract](../CLINICAL_OBSERVATION_CONTRACT.md)
retain the v0.1 health boundary and later module architecture.

## Target and source assumptions

The [frozen selection](../validation/ipop-a1c-working-fit-protocol-v1.json) asks
whether actual repeated A1C observations can distinguish effective switching
between three recorded bands. Cutoffs are 5.7 and 6.5 percent, applied to source
precision without rounding. [Zhou 2019, Results Overview](https://pmc.ncbi.nlm.nih.gov/articles/PMC6666404/#Sec2)
uses these thresholds; [NIDDK](https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test)
distinguishes laboratory categories from a confirmed diagnosis. A later lower
band is neither erased diagnosis history nor sustained treatment-free remission.

The exact two released files and full pre-filter namespace graph remain pinned
by the [previous intake](../IPOP_PREFLIGHT.md). The metadata namespace is used
conditionally for grouping. A consistent bijection can still be wrong. Percent
units, unnormalized A1C values and the specimen-day interpretation of the
derivative remain explicit working assumptions, rather than assertions certified
by plausible value ranges. The original study includes scheduled and illness
visits. Conditioning on their recorded times and assay availability does not
establish ignorable observation, survival or stopping.

Keep all source/linkage, unavailable-assay and single-observation denominators.
Quarantine a whole label with repeated eligible times; never average or deduplicate
its measurements. Subtract Decimal coordinates before floating-point conversion;
the unknown additive clock origin cancels without manufacturing calendar dates.
Quarantine a label if floating-point conversion loses finite strict ordering.
No GLU fasting interpretation, CL4 filter, prior diagnosis, treatment, death or
terminal censoring record is invented. Changing unmeasured treatment is part of
observed usual care, not a held-fixed intervention.

## Equations and alternatives

For bands 0, 1, 2, the primary generator has edges 0->1, 1->0, 1->2 and 2->1.
Off-diagonal rates are nonnegative per source day; each diagonal is minus its
row outflow. The exact observed-band path contributes
`sum log(exp(Q * elapsed_days)[previous_band, next_band])`, conditional on its
first measurement. Matrix exponentiation permits unobserved intermediate
switches between samples. It does not locate biological onset.

Retain an unrestricted six-edge generator, a training-only pooled categorical
predictor and exact persistence as alternatives. Impossible paths/predictions
remain impossible with an explicit flag; no positive likelihood floor is allowed.
The highest laboratory band remains reversible. No latent biological state or
free measurement-error matrix is estimated alongside these rates.

These are homogeneous Markov working models. HbA1c temporal averaging,
measurement variability, visit triggers, changing treatment and individual
heterogeneity can violate them. Good internal prediction would not resolve those
mechanisms. Poor prediction or indistinguishable rates are useful results.

## Identification, uncertainty and evaluation

The original selection protocol and registry were frozen and pushed before band-path inspection. A separately frozen [numerical amendment](../validation/ipop-a1c-numerical-amendment-v1.json) repairs synthetic optimizer and small-probability failures after aggregate band counts were inspected, before empirical fitting. Earlier
source intake is disclosed; the analysis is adaptive, used-source work. Assign
all admitted metadata labels by the frozen salted SHA256 rule before assay
eligibility, keeping every observation of a label in one partition. Never change
an inconvenient split. Reserved predictions use frozen fitted parameters, either
the preceding observation or only the first observation, at actual gaps. Report
log/Brier scores with observation and equal-label weighting for all alternatives.
This is internal evaluation, not independent-source or causal validation.

Check the actual design's probability Jacobian, singular values, boundaries and
rate profiles. Profile all rates under both CTMC structures, reoptimizing nuisance
rates. The declared rate cap is a computational search limit; open/capped/failed
profiles do not acquire finite confidence endpoints. A nominal chi-square profile
support rule assumes a correctly specified independent-label likelihood and regular
interior asymptotics. Finite-grid support is approximate, not exact confidence
endpoints or a clinical tolerance. Jacobian differences stay in the declared
nonnegative search domain, with forward/backward differences explicitly recorded
near zero/cap boundaries.

Resample whole training paths for 200 paired primary/IID fits and whole evaluation
paths for paired score differences. Retain failures instead of redrawing, disclose
boundary/cap counts, and report the four-rate covariance jointly. These conditional
sampling summaries omit structural, selection, treatment, unit, linkage and
transport uncertainty. They must not become independent engine priors.

## What remains to finish #57

The clinical target still requires a justified laboratory/diagnosis-history state
mapping; treatment and confirmation timing; ascertainment, missed visits,
competing death and withdrawal where the target depends on them; supported
population estimates and external predictive checks; then explicit U.S. transport
and annual-engine compatibility assessment. Mortality and dietary effects are not
identified by this laboratory-only process. Each missing record blocks its
dependent claim rather than every narrower working analysis. #57/#58 and the
v0.1 scientific acceptance criteria remain open.
