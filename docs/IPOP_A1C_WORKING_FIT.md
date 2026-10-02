# Learning from repeated A1C measurements

This analysis advances [#57](https://github.com/Crusonia/Demeter/issues/57) using
public repeated laboratory observations. It asks whether the timing of changes
between recorded A1C bands adds predictive information beyond persistence or a
pooled categorical predictor. It evaluates a conditional working process in the
selected panel, not diabetes onset, remission or a national dietary effect.

The [completed v2 aggregate](validation/ipop-a1c-working-result-v2.json) supplies
both working rate vectors. All six starts converged for each structure, and all
200 primary whole-path bootstrap fits succeeded. This explicit numerical repair
was committed and pushed at `d2f3ac7` before the rerun began; it was selected after
inspecting the failed original attempt. The likelihood, source selection,
convergence tolerance, profile grid and resampling design remained frozen.

The alternative's two direct outer-band edges are fitted at zero. Full local
numerical ranks (four and six) do not establish practical or global identification.
All ten profile grids completed without numerical failures, but some nuisance
solutions hit search caps; the alternative also retains zero-boundary and open
lower-grid limitations. No clinical confidence interval is reported.

The bootstrap retains one zero-boundary primary draw. One prediction comparison
was unavailable, leaving 200 contributing rate vectors and 199 finite paired
prediction comparisons. Covariance and percentiles describe sampling under this
conditional model, without resolving measurement, linkage, treatment, observation
selection or transport uncertainty. The [offline integrity audit](validation/ipop-a1c-working-integrity-v2.json)
checks the aggregate's bindings and mathematics. A separate
[simulation-preservation audit](validation/ipop-a1c-simulation-preservation-v2.json)
confirms that the four existing scenario outputs, sampling inputs, baseline checks
and observation reports retain their results apart from declared registry fingerprints.

### Original attempt remains visible

The [preserved v1 aggregate](validation/ipop-a1c-working-result-v1.json) records a
completed analysis with **both full-data CTMC estimates unresolved**. All six
prescribed starts for each structure reached the frozen 1000-iteration limit:
12 failed starts in total. Primary and general rate vectors, their profiles,
point identification and CTMC evaluation scores remain null. The pooled IID
categorical predictor is available; it does not establish time-dependent dynamics.
The exact no-switching null retains impossible changed-band predictions.

Of 200 whole-path bootstrap attempts, 157 primary fits failed and 43 succeeded.
Covariance and percentiles from those 43 draws are conditional on successful
finite estimation. They cannot replace the missing full-data point estimate or
establish an unconditional confidence interval. This failure is retained rather
than selecting a bootstrap draw as the reported model. A numerical repair must
be evaluated under a separate versioned protocol that discloses its post-outcome
selection. The completed v2 attempt above preserves this failed report unchanged.

The [program vision](PROJECT_VISION.md) still requires the full health slice
before agriculture, market and payer modules. This work informs health input
I-07 and observation formulation F-08; it does not turn the proposed value-chain
loops into empirical coefficients.

## Reproduce locally

Install the [locked environment](GETTING_STARTED.md). The quick offline audit
checks the committed aggregate report, evidence bindings and mathematical
consistency for each version, including the explicit unavailable v1 fits. The
v2 audit also checks the frozen profiles and resampling counts. It does not replay participant records
or independently validate clinical rates. When recreating transcendental profile
grid values, the audit permits up to four ULPs of platform roundoff. The derived
chi-square support cutoff permits eight ULPs, matching the measured macOS/Windows
inverse-CDF difference. Grid size, ordering, zero/cap endpoints and the fitted
coordinate remain exact. The
estimator's convergence settings and preserved report bytes are unchanged:

```bash
uv run python scripts/verify_ipop_a1c_working_fit.py
uv run python scripts/verify_ipop_a1c_working_fit.py --numerical-method exact_box_quadratic_v2
```

For full empirical reproduction, fetch the exact public
files once into a fresh ignored directory, then run the offline analysis:

```bash
uv run demeter data fetch-ipop --destination data/raw/ipop-a1c-v1
uv run demeter evidence ipop-a1c-working-fit --raw data/raw/ipop-a1c-v1 --output outputs/ipop-a1c-working-v1.json
```

These commands work in macOS/Linux terminals and Windows PowerShell. The fit
includes both structures, all frozen rate profiles and 200 whole-path bootstrap
replicates. Full fitting can take more than an hour; use the quick aggregate audit
for ordinary installation checks. Progress messages do
not expose participant records. Output must be a fresh path; existing files and
source/evidence paths are protected. Reuse the verified raw cache on later runs,
and choose a new report filename.

The [protocol](validation/ipop-a1c-working-fit-protocol-v1.json) and
[RFC](rfcs/RFC-57-ipop-a1c-working-fit.md) were committed and pushed before band
mapping and fitting. A separate
[numerical amendment](validation/ipop-a1c-numerical-amendment-v1.json) was frozen
after aggregate band counts, before empirical optimization, to correct failures
found with synthetic fixtures. Prior publication, code and source-intake inspection is
disclosed. This is adaptive used-source work with internal evaluation, not
preregistration or independent-source validation. The generic
[numerical library](../src/demeter/analysis/laboratory_panel.py) and
[source adapter](../src/demeter/analysis/ipop_a1c.py) are separate from the engine.

### Adaptive numerical repair

The [v2 numerical amendment](validation/ipop-a1c-numerical-amendment-v2.json)
was selected after the failed v1 outcomes were inspected. Synthetic weak-curvature
quadratics and rare-band panels isolate the internal direction solver's early
objective stop. V2 solves that small bounded quadratic by deterministic face
enumeration. The original likelihood convergence tolerance, iteration limit,
independent direct-gradient verification, data selection and 200-draw bootstrap
remain unchanged. Synthetic success establishes a numerical repair, not an
empirical or clinical result.

The explicit version leaves the default v1 replay intact. Reuse the verified
cache and select a fresh output path to run the repaired method:

```bash
uv run demeter evidence ipop-a1c-working-fit --numerical-method exact_box_quadratic_v2 --raw data/raw/ipop-a1c-v1 --output outputs/ipop-a1c-working-v2.json
```

V2 is a separate evidence-registry attempt with its completed aggregate registered
under `ipop_a1c_working_fit_v2`. The failed v1 report and its conditional 43-draw
summaries remain immutable. Both audits run offline in ordinary CI; full source
reproduction remains an explicit local operation.

## What the observations mean

An A1C measurement is grouped into below 5.7, 5.7 to below 6.5, or at least 6.5
percent, without rounding the original value. [The source study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6666404/#Sec2)
uses these cutoffs. [NIDDK](https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test)
explains the separate confirmation required for diagnosis. A lower later reading
does not establish treatment-free remission or erase a known diagnosis.

Percent units, unnormalized A1C and the derivative specimen-day clock are working
assumptions. Plausible values do not verify them. Grouping uses the separately
frozen producer sample-association hypothesis; consistency does not certify
identity. Death, withdrawal, missed visits, treatment and diagnostic history are
unknown. Their absence does not mean no event or no treatment.

The selection retains all 969 original clinical rows in the linkage denominator.
Of 951 admitted rows, 938 have finite A1C and usable times; 13 assay tokens remain
unavailable. Under the percent assumption, eligible band counts are 507, 402 and
29. All 104 admitted labels are allocated before assay filtering: calibration
has 88 labels/777 observations (78 repeated paths and 10 single observations);
evaluation has 16 labels/161 observations, all repeated. No label is moved to
improve the split. Repeated eligible times or loss of ordering on numerical
conversion quarantine an entire label; this release has neither condition.

## How to read a result

```mermaid
flowchart LR
    low["Band 0: A1C below 5.7%"] -->|"q01"| middle["Band 1: A1C 5.7% to below 6.5%"]
    middle -->|"q10"| low
    middle -->|"q12"| high["Band 2: A1C at least 6.5%"]
    high -->|"q21"| middle
```

The arrows describe effective changes in recorded readings under usual care.
Rates have reciprocal source-day units. An observation can cross two bands
between visits because intermediate readings are unobserved. A later low reading
does not reset diagnostic history or establish remission.

The primary process allows switching between adjacent bands in both directions.
The matrix exponential includes possible unobserved intermediate switches between
samples. An alternative permits all six directions. Neither represents latent
biological disease with an estimated assay-error model. A persistence benchmark
predicts no change; an IID benchmark uses training follow-up category frequencies.
Impossible predictions remain explicitly impossible, without a positive floor.

Rates have reciprocal source-day units. They summarize effective recorded-band
dynamics under changing usual care, conditional on first band, available tests
and recorded times. They are not annual clinical hazards or diet coefficients.
The homogeneous Markov and ignorable-observation assumptions can be wrong:
HbA1c averages earlier exposure, event visits can be informative and treatment
can change. Good prediction would not resolve those limitations.

Read the actual-design rank and rate profiles alongside optimizer convergence.
A full local numerical rank is not global or practical identification. Zero
boundaries, open/failed profiles and computational-cap hits remain visible;
finite grid endpoints are not exact confidence limits. The search cap is a
numerical workspace limit, not an empirical upper bound.

Evaluation scores compare next readings using either the preceding observed band
or only the first band, at actual elapsed times. The latter tests longer forecasts
without updating on intermediate evaluation outcomes. Log score rewards assigned
probability; Brier score measures the squared error of the complete category
probability vector. Report both equal-label and observation weighting so frequent
visitors do not silently determine every comparison. There is no sourced clinical
acceptance tolerance.

### Internal prediction has a mixed result

The table reports the completed v2 evaluation on 16 held-out source labels and
145 follow-up observations. Higher mean log score and lower Brier score are
better. Values below use equal label weighting; the aggregate also retains
observation weighting. These are internal used-source checks, without a clinical
acceptance threshold or independent-source validation.

| Predictor | One-step log score | One-step Brier | First-only log score | First-only Brier |
| --- | ---: | ---: | ---: | ---: |
| Adjacent recorded-band process | -0.522 | 0.294 | -0.712 | 0.433 |
| Six-edge alternative | -0.522 | 0.294 | -0.712 | 0.433 |
| Pooled IID bands | -0.840 | 0.529 | -0.840 | 0.529 |
| Exact persistence | Negative infinity | 0.273 | Negative infinity | 0.273 |

The time-dependent processes score better than IID on these point comparisons.
Their scores are almost identical because the alternative's direct outer-band
edges are zero. Persistence has a lower Brier score here but assigns zero
probability to 18 observed changes, making its log score negative infinity.
The first-only process forecast loses accuracy as it stops updating on intermediate
readings. In the 199 finite paired resamples, first-only observation-weighted
log-score and Brier differences against IID span both signs at the frozen
2.5th/97.5th percentiles. This panel does not establish reliable long-horizon
prediction, superiority on every metric or a clinical benefit.

Whole-path bootstrap draws preserve dependence within each label. Joint
covariance describes the four rates together; separate marginal summaries are
not independent priors. Paired model comparisons use identical resampled training
and evaluation labels. Failed draws are retained, not redrawn. Summaries over
successful finite draws are conditional on success. Boundary/cap counts and both
attempted and successful draw counts must accompany percentile summaries. The
v1 percentiles have only 43 contributing draws; 200 attempts do not give them
200-draw resolution. Sampling uncertainty
does not include linkage, units, treatment, visit selection, structure or transport.

## Remaining clinical work

This panel supplies an empirical laboratory-process working analysis, not the
full clinical target. Finishing #57 requires justified clinical-state/history
mapping, confirmation and treatment timing, competing events and stopping where
the target depends on them, supported population estimates, independent predictive
checks, and U.S. transport/annual-engine compatibility. A separate exposure
pathway is needed for #58. All active dietary simulations remain validation-only;
no scientific acceptance or engine activation follows from this analysis.

Next source appraisal should examine [Song et al., Shanghai follow-up](https://pmc.ncbi.nlm.nih.gov/articles/PMC4873952/)
for observed-label dispositions, deaths and missing glycemic assessments, and
[Shang et al., SNAC-K](https://pmc.ncbi.nlm.nih.gov/articles/PMC6851857/)
for repeated examinations, registry deaths and attrition. These are new candidates;
no parameters from them are admitted here. Reconcile source denominators,
measurement changes, event precedence, follow-up clocks and access conditions
before defining a likelihood. Aggregate endpoint counts alone do not identify the
clinical transition process or untreated remission.

The [official HAALSI documentation](https://data.agincourt.co.za/index.php/catalog/243/related-materials)
offers another public-use lead. A [metadata-only codebook review](validation/haalsi-codebook-coverage-v1.json)
pins the inspected document bytes. It lists repeated point-of-care glucose,
diabetes treatment/history definitions and respondent-status fields, but many
names are truncated and the table does not define complete value codes or
specimen/death/contact clocks. No HbA1c label was found in this document; this
does not establish absence from every release. Total hemoglobin is not HbA1c,
and survival/attrition weights are not event histories. Verify the full dictionary,
measurement timing and access terms before acquiring records or defining a
clinical likelihood. No participant files or model parameters were admitted.
