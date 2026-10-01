# Whitehall II: a follow-up endpoint likelihood

This increment implements one observation-level calculation for
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58): the published terminal FPG
labels among retained participants who initially had FPG-defined prediabetes.
It does not estimate annual clinical transitions. The engine and its scientific
release blockers remain unchanged.

The design trace is the health part of Q-03/RM-04 → P-02 → I-01/I-07/I-11/I-12 →
F-08 → T-01/T-02/T-05/T-06/T-08 in the [design registers](../design/README.md).
L-00 supplies conservation bookkeeping. Payer costs, externalities, value capture
and stakeholder-belief mechanisms are outside this increment.

## Observation and conditioning

[Vistisen et al. (2019)](https://doi.org/10.1007/s00125-019-4895-0) report
re-examination labels after phase 7 (2002–2004) at phase 9 (2007–2009), described
as approximately five years later. The selected supplement table contains
`Normoglycaemia` and `Prediabetes or diabetes` N cells in its **By FPG** block.
The latter is a collapsed category, not a progression-only count. The denominator
is their sum, conditional on source selection and paired classification.

An observed normal FPG label does not establish general metabolic health,
sustained untreated remission or absence of a prior diagnosis. Detailed drug and
diagnosis histories are unavailable in these aggregate cells. The exclusion of
known phase-9 diabetes for a continuous-change association analysis must not be
transferred to this categorical table. Later cardiovascular/death follow-up
starts at phase 9; it is not the competing-death partition during phases 7–9.
Unobserved participants are not assigned outcomes. Overlapping FPG, 2hPG and
HbA1c groups are not pooled as independent observations.

## Two analysis modes

The descriptive mode reports `y/N`: the observed normal-label fraction in this
selected source sample. It supplies no sampling interval without a sampling
model. The working-likelihood mode explicitly assumes independent Bernoulli
labels with a common probability p, conditional on N:

```text
K | N,p ~ Binomial(N,p)
L(p) = choose(N,y) p^y (1-p)^(N-y)
p_hat = y/N
```

This is a fitted endpoint probability under a declared working model. It is not
a clinical transition fit or reconstruction of the paper's CVD regression. The
publication does not establish the working iid/constant-p assumptions. Selection,
clustering, varying visit times, measurement error and history remain outside
this likelihood. Its interval cannot quantify those uncertainties.

The analysis design selects a two-sided, equal-tail **Clopper–Pearson** interval
at confidence 0.95, fixed before the planned selected-cell extraction but after
prior/incidental result exposure. This is an analyst setting, not a source
estimate or published interval. For alpha = 1 − confidence:

```text
lower = 0 if y=0, else BetaQuantile(alpha/2; y,N-y+1)
upper = 1 if y=N, else BetaQuantile(1-alpha/2; y+1,N-y)
```

The method has coverage at least the selected level **within the assumed
binomial experiment**, not across unmodeled cohort selection or misclassification.
See the [official R method description](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/binom.test.html),
[SciPy binomial API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html)
and [beta quantile API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.beta.html).
The implementation uses the locked project dependency. No null hypothesis,
Bayesian prior or posterior is introduced.

## Why this cannot identify annual rates

An illustrative two-state continuous-time model, starting in a toy nonnormal
state P, has terminal normal-state probability

```text
Pr(H at t | P at 0) = b/(a+b) × [1 − exp(−(a+b)t)]
```

where a is H→P and b is P→H. One terminal probability does not determine both
rates: different rate sums and return fractions can give the same terminal
probability. Tests illustrate this with synthetic inputs only. No observed
Whitehall probability is inverted or used to optimize rate witnesses.

This toy omits diabetes, treatment, death, measurement error and selection. It is
an educational ambiguity example, not a clinical model or a formal identification
proof for Demeter's actual annual operator. Dividing `y/N` by five, or imposing an
exact common five-year duration, would not resolve the missing histories.

## Reproduction and evaluation

The [frozen protocol](../validation/whitehall-fpg-endpoint-protocol-v1.json) binds
two static PDF byte snapshots, exact table/row/column selection, a main-article
denominator/numerator crosscheck, working assumptions and failure handling.
The [receipts](../validation/whitehall-fpg-source-receipts-v1.json) preserve actual
historical acquisition times separately from later local byte verification.
Dynamic HTML/access pages are historical context rather than numerical runtime
dependencies. Complete publications remain fetch-only.

Selected counts were null at the design freeze. Earlier automatic snippets and
an incidental abstract heading scan had already exposed descriptive results.
This chronology is disclosed; the analysis is neither preregistered before
outcome inspection nor independent/held-out validation. Duplicated main and
supplement numbers are same-source consistency checks.

Source checksum, document identity, row/header/column binding, strict integer
counts and the crosscheck must all pass before working likelihood evaluation.
Missing or changed sources produce a saved aggregate failure and nonzero CLI
exit; no source repair, silent repinning or replacement estimate is permitted.
Impossible likelihood boundaries are explicit zero-probability events with a
JSON-null log value; public output never contains NaN or Infinity.

Software tests cover meaningful boundary/domain arithmetic, normalization,
interval inversion, synthetic ambiguity, parser drift and source/output
immutability. Before/after simulation checks distinguish registry provenance
changes from model-output changes. Source reproduction, software correctness,
protected CI, merge and external human scientific review are separate judgments.

Full #57/#58 acceptance still requires an adequate clinical observation model,
timing/history/selection/death evidence and identifiable transition parameters;
diet dose/substitution/lag, U.S. transport and independent clinical evaluation
remain unresolved. This increment cannot close #1 or #27 or justify health,
healthcare-cost or investment conclusions.
