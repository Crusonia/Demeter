# Source-native nominal observations

Demeter now preserves the public Kerala trial's recorded observations in a
private, immutable adapter. A separate **validation-only** likelihood evaluator
accepts explicitly declared probabilities between nominal visit indices. No
clinical transition, observation-channel probability or mortality coefficient
is fitted from these records.

This implements the first observation-design steps in
[the source-specific design](KERALA_OBSERVATION_MODEL.md), with trace
I-11/I-12 → F-08 → T-05/T-08. It advances source compatibility for #57 while
keeping the five clinical calibration blockers unresolved.

## Reproduce the checks

From the repository root on Windows, macOS or Linux:

```bash
uv run demeter evidence kerala-observations --output outputs/kerala-observations.json
uv run python scripts/verify_kerala_observations.py
uv run pytest tests/test_kerala_observations.py tests/test_nominal_observation_likelihood.py
```

The default command verifies the registry, source-admission chain, frozen
protocol, transform checksum, aggregate schema and report bytes **offline**.
It does not inspect participant values or claim to reproduce them. For a private
cache containing the two checksum-pinned public workbooks:

```bash
uv run python scripts/verify_kerala_observations.py --source-cache outputs/kerala-v3
uv run demeter evidence kerala-observations --source-cache outputs/kerala-v3 --output outputs/kerala-observations-replayed.json
```

This replay validates the existing source admission before reading only selected
cells. The public aggregate report must reproduce exactly; a mismatch fails.
The CLI protects sources and frozen records and writes exclusively to a new
output file. Private source keys, cluster keys, assays and labeled multiwave
tuples are not exported or committed. Installation instructions are in
[Getting started](GETTING_STARTED.md); source acquisition and rights are in
[Kerala source coverage](KERALA_SOURCE_COVERAGE.md).

## What the public records establish

The adapter retains all **1,007** source participants and **3,021** nominal slots
at Baseline, 12 months and 24 months. All selected wide/long clinical copies,
assignment labels and typed cluster keys must agree. Numeric and string keys
are kept distinct; duplicate or missing linkage fails instead of dropping a
participant. A slot's presence does not establish attendance or survival.

The frozen report's source flag algebra is:

| Stored-record check | Count |
| --- | ---: |
| Fully interpretable total/first-suffix/second-suffix flag triples | 872 |
| Positive in either suffix | 147 |
| Positive in both suffixes | 0 |
| Total No with a positive suffix | 0 |
| Total Yes with both suffixes No | 0 |
| Unknown total with a positive suffix | 0 |

The horizon-total marginal contains 147 Yes, 772 No and 88 absent cells.
The two suffix flags have 88 and 59 Yes cells respectively. Their nonoverlap
and union are consistent with a coding convention that records new diagnoses
at each assessment. They **do not prove** interval semantics, exact first-onset
times or biological disease-free status for records marked No.

Earlier positive suffix evidence remains recorded when a later suffix is No,
blank or uninterpretable. A positive horizon-total flag is not backdated to an
earlier visit. Neither flag becomes a confirmed clinical diagnosis, and no
seen positive is not evidence of no prior diagnosis.

The ADA category and ADA diabetes flag agree where both are interpretable.
Later two-hour cells are absent after earlier ADA-positive evidence, consistent
with the publication's OGTT-omission policy. This Boolean compatibility check
does not assign an absence reason or diagnosis route to a person. An incidence
flag alone does not establish the policy's OGTT diagnosis trigger. A medication
Yes alone does not establish physician diagnosis. The policy and endpoint
definition come from the [completed trial](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1002575),
not from field-name inference.

Assay availability means **a numeric cell is stored**, not that a valid test
was performed. Exact assay, contact, diagnosis and death times, individual loss
reasons and repeat-test confirmation remain unknown. An unevaluable consistency
check returns null, not a vacuous pass. The unlabeled pattern-size histogram
conserves every retained participant; its cells have no published trajectory
labels and are not sampling weights or probabilities.

The protocol was committed before this adapter's new joint diagnostics, but
after published results and prior selected marginals had been seen. This is
used-source development, **not preregistration or independent validation**.
Earlier immutable source protocols and frozen reports remain intact.

## What the likelihood evaluator proves

The separate Python evaluator takes one declared linked path, an initial state
distribution, consecutive nominal-interval stochastic matrices, exhaustive
joint observation channels and observed tokens. It never converts visit labels
to years, days or hazards. Every slot includes a token, including unavailable
measurements; missing cells do not automatically become an all-ones mask.

Channels can condition on the entire preceding observation-token prefix, so a
declared model can represent testing that depends on prior observations.
Baseline joint probability and probability conditional on the baseline token
are explicit alternatives. Conditioning on an already-selected cohort is
separate from fitting its selection process; the evaluator does not supply a
selection model or a product likelihood across people or clusters.

Synthetic tests enumerate hidden states and full token paths, check normalization
and explicit missingness dependence, preserve death and diagnosis-history
invariants, and distinguish impossible paths from floating-point underflow.
Log-domain filtering preserves tiny positive paths and later-relevant small
posteriors. Input row deviations are reported; empirical rows are not silently
renormalized. Caller tolerances must be positive and at most `1e-12`; they allow
numerical roundoff, never materially deficient or excessive probability mass.
Both the standalone transition validator and path evaluator enforce this cap.
These are software properties, not source calibration evidence.

See [the kernel](../src/demeter/analysis/nominal_observation_likelihood.py) and
[its synthetic tests](../tests/test_nominal_observation_likelihood.py).
The source adapter does not construct its latent state space, map source flags
to clinical history, or supply its emission probabilities.

## The next empirical decision

Before source-specific estimation, define an observable estimand and the full
joint label/availability channel, preserve community-cluster and repeated-person
dependence, and declare selection and unexplained missingness assumptions.
Test identification and sensitivity at the documented nominal resolution.
An observed-label working model would remain distinct from latent biological
transitions, annual engine parameters and an assigned-regimen causal effect.

Unlinked deaths and unknown endpoint completions remain the separate
[endpoint-bound analysis](KERALA_ENDPOINT_BOUNDS.md). The model still needs
verified clinical transition observation semantics, observation timing,
measurement error, external evaluation and baseline transition fit before
clinical calibration can be activated. Neither this release nor a source-native
working fit alone clears those requirements.
