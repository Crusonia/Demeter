# RFC-57 extension: Chen timing and observation contract

Date: September 30, 2026. Status: descriptive audit and proposed identification
decision; external expert review pending. Parent: [RFC-57](RFC-57-longitudinal-identification.md).
Design links: I-01/I-07/I-11/I-12, P-02, F-08 and T-05/T-08. Business externalities
and value capture are inapplicable to this input audit. The v0.1 boundary applies.

## Question and chronology

Can the released follow-up column account for the paper's total person-years,
and does a separately calculated mean explain its reported median? Are the
durations compatible with the reported calendar window under explicit year
conventions? What observation contract would a subsequent hazard fit require?

The [frozen protocol](../validation/chen-followup-timing-protocol-v1.json) is
written after reading the paper, metadata, headers and the prior intake results,
including the failed median check. It precedes the new release-wide sums, means,
day-grid diagnostics and calendar-envelope counts. It is a used-source diagnostic,
with no independent holdout. The original protocol and failed receipt stay intact.

## Locked source diagnostics

Read the pinned workbook through the existing read-only extractor. Keep missing
and invalid observations explicit, export aggregates only and retain every record.
Report all-release and recorded-endpoint summaries. A subgroup cannot replace the
published whole-cohort target. Compare person-years, mean and ordinary median
separately at the displayed precision. A mean match cannot repair a median failure
or establish that the paper mislabeled its statistic; the article does not specify
a censoring-adjusted follow-up median estimator.

Check integer-day proximity and the entire reported calendar envelope under each
prespecified candidate year conversion. These checks cannot recover visit dates.
Do not choose a scale, drop a tail or adjust the source to obtain agreement.
These fixed-release diagnostics have no sampling intervals; selection, measurement
and transport uncertainty remain unresolved. All numeric constants are mirrored
in the evidence registry before executing the audit.

## Observation and likelihood decision

The release's baseline/final glucose and recorded diabetes flags can support
descriptive observation accounting under a separately specified measurement
definition. A below-threshold final glucose following a recorded diagnosis keeps
its diagnosis history. Missing glucose and undefined diagnosis blanks stay visible.
Recorded incident fraction has a released-cohort denominator and varying stopping
times; it is not a common-horizon risk or annual transition rate.

The paper says follow-up ends at diagnosis or final visit. Consequently, it is
not justified to treat every released duration as an externally scheduled panel
visit. Observation modes require different likelihood contributions:

| Mode | Candidate contribution | Evidence needed |
| --- | --- | --- |
| Exogenous panel | `[exp(Q t)]_ij` for observed states | Visit timing independent of the unobserved state process, or a modeled observation process; defensible state/measurement mapping |
| Exact first detected event | `[exp(A t) r]_i`, where A is the transient generator and r its exit hazards | Continuously observed first event and known entry/administrative stopping; detection need not equal biological onset |
| Interval-detected first event | Integral of the first-event density over the last-negative/first-positive interval | Documented observation interval and ascertainment process |
| Unresolved | No supported hazard fit | Current Chen disposition |

A generator's hazards have reciprocal-time units. Matrix-exponential panel
probabilities and interval-event probabilities are dimensionless; an exact-event
density has reciprocal-time units. These are proposed mathematical contracts,
with no new coefficients or engine equations. Death, treatment and post-diagnosis
trajectories cannot be supplied by invented records. The author's
[msm observation documentation](https://chjackson.github.io/msm/reference/msm.html)
distinguishes panel observations from exact transitions; its
[manual](https://github.com/chjackson/msm/blob/master/vignettes/msm-manual.Rnw)
also discusses informative sampling times. This is methodology, not validation
of a Chen likelihood or a requirement to adopt that software.

Two appropriately observed visits can identify some simple reversible models
under restrictive assumptions. The obstacle here is the unverified observation,
stopping, measurement and selection contract. A timing-summary agreement alone
does not resolve those requirements. Baseline diabetes was excluded and follow-up
stops at diagnosis, so post-diabetes remission/relapse histories are unavailable;
death histories and dietary effects are also unavailable.

## Delivery and scientific disposition

Implement a separate CLI audit and aggregate receipt, with source/protocol/reader/
transform hashes and a machine-readable support decision. Test complete versus
partial denominators, invalid endpoint partitioning, empty groups, mean/median
distinction, calendar-envelope diagnostics and source/protocol drift with synthetic
fixtures. Preserve the old failed result byte for byte. Compare canonical scenarios
before/after, audit packaging and run the full software checks.

If public documentation cannot resolve the timing/observation contract, retain
Chen as a benchmark and continue toward a compatible repeated-observation or
published aggregate-transition package. Descriptive work and synthetic
identification experiments can continue under their own frozen protocols. An
unanswered rounded-median question is not a dependency for all public research.

No scientific release criterion is waived and #57 remains open. The work is
Codex-assisted for the Food is Health-affiliated project; automated scientific
critique is not independent human review. Clinical/causal acceptance and external
expert review remain pending.
