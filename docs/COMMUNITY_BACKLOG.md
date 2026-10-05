# Help strengthen Demeter's evidence and validation

Demeter is an open model built over time to make the connections between food,
health, agriculture and the economy testable. We need people who can identify
useful datasets, challenge our assumptions, independently check calculations,
and help a newcomer reproduce a run. You do not need to agree with the Food is
Health thesis. A null result, an adverse trade-off or a well-documented failure
can improve the model as much as a successful prediction.

The current implementation priority is the health vertical slice:
dietary exposure → metabolic states → mortality → life expectancy and healthy
life expectancy. The broader value-chain ambition remains in the
[project vision](PROJECT_VISION.md). It is developed in stages, rather than
implemented all at once.

As of October 5, 2026, software validation passes while scientific release
remains blocked by unresolved national transition hazards, clinical state
initialization, dietary causal effects/dose/lag, state-sensitive mortality and
end-to-end dietary historical validation. See the live
[v0.1 status](V0_1_STATUS.md), [evidence gaps](EVIDENCE_GAPS.md) and
[acceptance issue #1](https://github.com/Crusonia/Demeter/issues/1).
Rerun `uv run demeter validate` for the checkout you are testing.
Health scenarios remain **validation-only** while their material inputs are
synthetic or unresolved.

## Choose a bounded contribution

This table links actual community issues. Their GitHub status is authoritative;
the priority column describes sequence, not a claim that the work is finished.
Each issue includes a first deliverable, completion criteria and starting
documents. The existing [transition calibration #57](https://github.com/Crusonia/Demeter/issues/57)
and [dietary pathway #58](https://github.com/Crusonia/Demeter/issues/58) remain
the scientific umbrellas; completing a child appraisal does not close them.

| Priority | Community issue | Who can help |
| --- | --- | --- |
| First | [#115: Find a timed longitudinal glycemic dataset with death and attrition accounting](https://github.com/Crusonia/Demeter/issues/115) | Cohort investigators / data stewards |
| First | [#116: Appraise U.S. age/sex metabolic-state initialization](https://github.com/Crusonia/Demeter/issues/116) | Survey statisticians / clinicians |
| First | [#117: Appraise one causal dietary exposure-to-health pathway](https://github.com/Crusonia/Demeter/issues/117) | Trial investigators / nutrition and causal-inference researchers |
| Next | [#118: Review metabolic-state mortality and national transport](https://github.com/Crusonia/Demeter/issues/118) | Epidemiologists / survival analysts |
| Next | [#119: Identify an independent historical health holdout and freeze its protocol](https://github.com/Crusonia/Demeter/issues/119) | Data stewards / independent validation researchers |
| First | [#120: Independently challenge the clinical observation and identification contract](https://github.com/Crusonia/Demeter/issues/120) | Clinicians / biostatisticians |
| Next | [#121: Verify health arithmetic with independently derived numerical oracles](https://github.com/Crusonia/Demeter/issues/121) | Numerical analysts / system-dynamics developers |
| Next | [#122: Audit uncertainty, dependence and Monte Carlo convergence](https://github.com/Crusonia/Demeter/issues/122) | Statisticians / uncertainty-analysis developers |
| Start here | [#123: Reproduce a first run on macOS, Linux or Windows](https://github.com/Crusonia/Demeter/issues/123) | First-time users / platform testers |
| Start here | [#124: Audit one public evidence receipt and derived-data chain](https://github.com/Crusonia/Demeter/issues/124) | Careful readers / data engineers |
| Design only | [#125: Appraise one cross-industry feedback or externality before implementation](https://github.com/Crusonia/Demeter/issues/125) | Farmers / food operators / healthcare and climate researchers |

**First:** compatible clinical data and specialist appraisal can unblock
identification. **Next:** validation protocols and numerical checks can proceed
now; empirical prediction tests depend on identified parameters and admitted
data. **Start here:** one platform or one public source row is enough for a
beginner contribution. **Design only:** later-phase source inventories and
falsification plans are welcome now, with runtime work deferred until the
health gate is met.

Comment on an issue with the small piece you want to tackle. You can work on
one source, one equation, one platform or one counterexample. The maintainer
can split a follow-up or record complementary independent reviews. Do not
feel responsible for resolving an entire clinical gate alone.
Use the [contribution guide](../CONTRIBUTING.md) for forks and pull requests.
Carter Williams reviews and merges community contributions.

## If you have access to a useful dataset

Start with a [dataset offer](https://github.com/Crusonia/Demeter/issues/new?template=dataset-offer.yml)
or a metadata-only comment on the relevant issue. A link and a description are
enough; no file upload or completed analysis is required. Include what you know,
and mark unknowns explicitly:

- Publisher/cohort, release/version, primary publication, dictionary and exact
  field/table names.
- Population, recruitment, geography, period, age/sex coverage and selection.
- What is measured, units, definitions, linkage and actual measurement clocks;
  diagnosis/treatment history, deaths, missed visits and follow-up boundaries
  where available.
- Survey design, uncertainty, shared participants and other dependence.
- Access conditions, analysis rights, redistribution and output restrictions;
  whether you can lawfully run a specified analysis locally or produce permitted
  sufficient aggregates.

Public sources are preferred when equally suitable. Controlled-access or
institution-held data can still be useful: describe capabilities and the
lawful access route first. An open article is not permission to redistribute
participant data. **Do not post participant records, linkage keys, credentials,
restricted files or confidential outputs in public issues or PRs.** Even
aggregate results need the applicable output/disclosure permissions.

The [longitudinal checklist](PUBLIC_LONGITUDINAL_DATA_REQUIREMENTS.md) explains
why separate visit marginals, a mean follow-up time or a published hazard ratio
may be insufficient. Linked observations or genuinely sufficient jointly timed
aggregates are candidates; either still needs an identification appraisal.
A new source offer does not waive an existing source-specific admission contract.

An offer proceeds through distinct checkpoints:

1. **Source appraisal:** inspect permitted metadata and definitions; record gaps,
   rights, applicability and a proposed observation contract.
2. **Authorized acquisition/analysis:** freeze the protocol, source identities,
   estimand, likelihood, missingness and uncertainty treatment before admitted
   data inspection or fitting. Obtain the access and output permissions needed
   for that specific source; a GitHub issue is not data-use authorization.
3. **Reproducible evidence contribution:** preserve immutable source receipts,
   separate raw/derived/model-ready artifacts, reproducible transforms and
   permitted outputs. Use synthetic fixtures for public adapter tests when
   participant files cannot be shared.
4. **Scientific acceptance:** independent review, identification and appropriate
   evaluation determine whether a parameter can become active. Record population,
   units, transformations, uncertainty, evidence strength and status in
   `evidence/parameters.yaml`; source availability alone is insufficient.

See [scientific review](SCIENTIFIC_REVIEW.md) and the [RFC process](rfcs/README.md).
A dataset incompatible with the present states can still be a useful benchmark
or a reason to revise a proposal; do not force it into a clinical parameter.

## If you can independently test the model

Use an [independent validation report](https://github.com/Crusonia/Demeter/issues/new?template=independent-validation.yml)
or contribute to the relevant testing issue. Report the exact commit and source
versions, environment, commands, expected/actual results and limitations.
Define a failure criterion before checking results where practical. Separate
**PASS**, **FAIL**, **BLOCKED** and **UNRESOLVED**; a blocked data check is not a
passing model check.

| Check | What it can establish | What it cannot establish on its own |
| --- | --- | --- |
| Fresh installation and offline replay | Another user can reproduce the documented computation and inspect labels | Clinical validity or a dietary benefit |
| Source transcription, checksum and rebuild | Provenance and a transformation match the pinned source | Independence, causal applicability or predictive accuracy |
| Implementation parity | Two implementations agree under stated inputs/conventions | Correctness if they share the same mistaken equation |
| Analytical or independently derived oracle | Arithmetic, units, conservation and numerical behavior under declared cases | Real-world parameter values or clinical state definitions |
| Clinical/identification review | Whether definitions and observations support the intended estimand | National transport or empirical prediction without suitable evidence |
| Frozen independent historical evaluation | Predictive performance for a declared population, endpoint and horizon | Causality or validity outside that population and exposure range |

Keep failed cases and competing explanations. Synthetic data are useful for
testing code and must be labeled as such. They cannot turn a dietary lifespan
estimate into a scientific finding. Previously inspected or fitted data cannot
be described as an untouched holdout.

## Help develop the larger system without skipping the health gate

The [design inputs](design/README.md) register loops, externalities, inputs,
equations and stakeholder rigidities as hypotheses. A contribution can appraise
one coupling now: food/climate (P-03), chronic/acute care demand (P-04),
microbiome/agriculture (P-05), or land/productivity/nutrient-capacity trades
(P-06/P-07). Trace the selected design IDs to supporting and opposing sources,
uncertainty, actor incidence and a proposed test.

For example, reduced chronic-disease volume can coexist with more acute,
refractory, previously undiagnosed or added-years care. National land totals
can conceal concentrated local effects, and equal acres need not yield equal
nutrient capacity. These are questions for the model to test; neither savings
nor a positive spillover is assured.

Only healthy longevity is currently computable, with validation-only limits.
Future health-adjusted TFP, productive capacity/health-inclusive GDP, industry
accounts and emissions/land guardrails remain staged research. Do not generate
them from placeholder inputs. Link later-phase proposals to the existing
[#10–#15 roadmap](POST_V0_1_ROADMAP.md) rather than adding premature runtime
modules or investment conclusions.

## How the backlog stays useful

For each contribution, the maintainer records its scope, links the PR/report,
and distinguishes software verification from scientific acceptance. Close an
appraisal ticket when its reviewed deliverable is complete, including a finding
of incompatibility; keep the parent scientific gate open until its criteria
are met. Capture unresolved questions as follow-ups rather than silently
declaring them solved. Update this table when priorities or links change, and
link implemented evidence, equations and tests back to their design IDs.

