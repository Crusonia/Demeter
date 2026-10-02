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
blocks. Each summary states its contributing and unavailable counts. A block's
covariance uses the same draws for all its entries; covariance entries from
different subsets are never assembled into one purported joint matrix. The
original eight-coordinate covariance remains visible.

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

```text
uv run python scripts/replay_ipop_predictive_supplement.py --raw data/raw/ipop-v1 --freeze-commit FROZEN_COMMIT --output outputs/ipop-predictive-supplement.json
```

Identifier-free aggregate score vectors allow an offline arithmetic audit.
They contain no participant labels, assays, times, resampled label indices or
individual predictions. Reconstructing summary arithmetic does not independently
verify source fitting or clinical prediction.

All summaries remain conditional working-model sampling uncertainty. They omit
measurement/linkage ambiguity, treatment, informative observation or stopping,
model structure, transport and causal uncertainty. No clinical diagnosis,
remission, dietary effect, mortality inference, U.S. calibration or engine
activation follows from this supplement.
