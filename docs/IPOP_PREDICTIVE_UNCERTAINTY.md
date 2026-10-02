# Predictive uncertainty with separate metric support

Log score and Brier score answer different prediction questions. Log score can
be negative infinity when a valid model assigns zero probability to an observed
band. Brier score can still be finite because it measures the squared error of
the whole probability vector. Missing log-score support must not automatically
remove otherwise usable Brier differences from a metric-specific summary.

The [original v2 analysis](IPOP_A1C_WORKING_FIT.md) uses 199 bootstrap draws with
all eight paired comparisons finite. Its covariance and percentiles correctly
describe that complete-vector conditional subset. Its Brier summaries share that
restriction; they are not uncertainty summaries over every usable Brier draw.

The [separately frozen reporting protocol](validation/ipop-a1c-predictive-summary-protocol-v1.json)
adds per-coordinate summaries and separate four-coordinate log-score and Brier
blocks. The eight coordinates combine two forecast modes (one-step and
first-observation-only), two metrics, and two weighting rules (equal label and
equal follow-up observation). Each summary states its contributing and unavailable counts. A block's
covariance uses the same draws for all its entries; covariance entries from
different subsets are never assembled into one purported joint matrix. The
original eight-coordinate covariance remains visible.

The [completed supplement](validation/ipop-a1c-predictive-summary-result-v1.json)
exactly reproduces the original rate and complete-vector summaries. Its retained
200 aggregate score vectors give these measured supports:

| Summary | Finite draws | Unavailable draws |
| --- | ---: | ---: |
| Original eight-coordinate vector | 199 | 1 |
| Four-coordinate log-score block | 199 | 1 |
| Four-coordinate Brier block | 200 | 0 |
| Each one-step log-score coordinate | 199 | 1 |
| Each first-only log-score coordinate | 200 | 0 |
| Each Brier coordinate | 200 | 0 |

The first-only log coordinates also retain the previously excluded draw. These
coordinate summaries are dependent marginals, not independent priors. The
reported `1/n` is contributing-draw granularity; it is not measurement accuracy
or confidence. A null difference is unavailable, never zero.

This is a post-outcome reporting amendment selected after the completed v2 result
and review were inspected. It replays only the same 200 whole-label bootstrap
attempts, seed, selection and fitting controls. It does not replace failed draws,
change probabilities, rerun full-data fits/profiles, or overwrite v1/v2 evidence.
Exact same-platform reproduction of the original rate and complete-vector
summaries is required before a supplemental result can be published.

The legacy bootstrap records coarsen unsupported log differences into
`unavailable_or_nonfinite_difference`. This supplement preserves that status;
it cannot infer an infinity's sign or cause from a null difference. Known fit
unavailability and numerical prediction failures remain distinct. An unavailable
comparison is not automatically a failed fit.

For a verified cache, a maintainer first freezes and pushes the reporting code
and protocol, then uses that full commit identity and a fresh output path:

The published annotated tag preserves the original freeze after squash merge
and is protected against movement and deletion.
Use a Git clone and fetch that tag explicitly, including for a shallow checkout:

```text
git fetch origin tag demeter-ipop-predictive-summary-freeze-v1
uv run python scripts/run_ipop_predictive_supplement.py --raw data/raw/ipop-a1c-v1 --output outputs/ipop-predictive-supplement.json
```

The supported launcher defaults to the exact frozen commit
`6210db409e890ef3811afc1c01282d232e4a1dd7`. It creates missing output directories
and checks publication storage before fitting. Existing output files are never
overwritten. The original replay script stays byte-for-byte frozen; the new
launcher handles publication setup around it. An extracted source distribution
can perform the offline arithmetic audit below, but empirical replay needs the
Git snapshot and a separately verified participant cache.

Reconstruct the committed summary arithmetic offline, without participant data:

```text
uv run python scripts/verify_ipop_predictive_supplement.py
```

Identifier-free aggregate score vectors allow an offline arithmetic audit.
They contain no participant labels, assays, times, resampled label indices or
individual predictions. Reconstructing summary arithmetic does not independently
verify source fitting, the historical Git snapshot/freeze chronology, or clinical
prediction. The actual replay verifies the declared Git snapshot before source
access; the offline audit checks current implementation and artifact hashes.

All summaries remain conditional working-model sampling uncertainty. They omit
measurement/linkage ambiguity, treatment, informative observation or stopping,
model structure, transport and causal uncertainty. No clinical diagnosis,
remission, dietary effect, mortality inference, U.S. calibration or engine
activation follows from this supplement.
