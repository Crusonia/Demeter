# What missing outcomes allow us to conclude

Demeter can now calculate exact completion bounds for the Kerala trial's
**recorded diabetes endpoint**. This is an observation analysis for #57/#58,
not a fitted biological transition model or an isolated food effect. It feeds
I-11/I-12 → F-08 → T-05/T-08 in the [design records](design/README.md).

After [setup](GETTING_STARTED.md), run from the repository root:

```bash
uv run demeter evidence kerala-endpoints --output outputs/kerala-endpoints.json
```

Use a new output filename on each run. The default command works offline with
registered aggregate counts and verifies the existing Kerala source package.
It does not download data or claim that it has re-read the raw source.

The [primary publication](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1002575)
reports 79 positive endpoints among 463 known control endpoints and 68 among
456 known intervention endpoints. The assigned cohorts contain 507 and 500
people. There are therefore **44 unknown endpoints in each arm**. The
[pinned public workbook](https://doi.org/10.6084/m9.figshare.5661610.v3)
reproduces these arm-specific counts; raw participant files remain fetch-only.

| Assigned cohort | Recorded positive | Known negative | Unknown endpoint | Positive fraction under all compatible binary completions |
| --- | ---: | ---: | ---: | ---: |
| Control, 507 people | 79 | 384 | 44 | 15.58%–24.26% |
| Intervention, 500 people | 68 | 388 | 44 | 13.60%–22.40% |

The intervention-minus-control fraction can range from **−10.66 to +6.82
percentage points**. These are deterministic finite-cohort bounds, **not
confidence intervals**. Both directions are compatible with the unknown
endpoints. The range makes no claim about misclassification, unobserved
biological onset, sampling uncertainty or transport to another population.
In particular, a source-coded No is a recorded label under that person's
available ascertainment, not proof that no biological diabetes occurred
throughout the full nominal 24 months. Hidden diagnoses among coded No records
require an additional measurement model; these completion bounds do not cover them.

The command also exposes a tipping sensitivity. If all 44 unknown control
endpoints were negative, ten additional positive intervention endpoints would
make its all-assigned fraction higher. This is a hypothetical completion, not
an estimate that those outcomes occurred. Counts of compatible aggregate
completion pairs are not probabilities; they receive no posterior or equal
probability weights. Cluster and repeated-person dependence are not replaced
with independent-binomial intervals.

## Equations and death handling

Let N be the original assigned cohort, K its known endpoints, Y its recorded
positive endpoints and U = N − K. The completed positive count lies in
[Y, Y + U]. Divide by N for the all-assigned fraction. A diagnosis may precede
death, so deaths are not automatically subtracted from unknown endpoints or
recorded diagnoses. Lower later glucose does not erase that history.

The publication's Figure 1 reports one control and two intervention deaths at
both follow-up horizons. Those counts are cumulative and unlinked to endpoint
records. Complete death ascertainment among every assigned person is not
independently established. Survivor fractions therefore remain unavailable
by default.

To inspect a separate sensitivity under an **extra assumption** that these
death counts exhaust mortality in the same cohorts:

```bash
uv run demeter evidence kerala-endpoints --assume-complete-deaths --output outputs/kerala-endpoints-survivor-assumption.json
```

With that assumption and D unlinked deaths, the survivor positive count ranges
from max(0, Y − D) to min(N − D, Y + U), with denominator N − D. All death
allocations consistent with the supplied group counts remain possible. The
components are coupled by their shared death total; their separate extrema
cannot all be chosen independently. Empty/all-dead denominators produce null
fractions, never zero risk. The output explicitly keeps death completeness
unverified even when the assumption is selected. This survivor comparison is
a selected, distinct estimand and has no automatic causal interpretation.

## Reproduce and inspect

With separately acquired exact public workbooks and the pinned primary PDF in
an ignored cache:

```bash
uv run demeter evidence kerala-endpoints --source-cache outputs/kerala-v3 --publication outputs/kerala-v3/thankappan2018-primary-publication.pdf --output outputs/kerala-endpoints-source-replay.json
```

This verifies workbook bytes, headers and the registered aggregate appraisal,
then privately calculates broad arm-by-total-endpoint counts and checks them
against the publication transcription. PDF text extraction independently
checks the six assigned/known/positive counts on page 10. Figure 1 is an image;
death counts retain their prior visual-source appraisal and are **not** claimed
to be automatically extracted. No person, cluster, assay, or labeled multiwave
trajectory is exported. Public replay needs no authoring Git history.

The eight observed count parameters live in `evidence/parameters.yaml`, each
with source, population, geography, timing, units and a benchmark-only role.
Their fixed count status does not resolve population or missing-outcome
uncertainty. The original after-source-inspection protocol and its additive
page-locator/death-completeness amendment remain immutable. The default
[frozen report](validation/kerala-endpoint-bounds-v1.json) has no raw-replay
claim; the verifier compares its full content exactly.

```bash
uv run python scripts/verify_kerala_endpoints.py
uv run pytest tests/test_endpoint_bounds.py tests/test_kerala_endpoints.py tests/test_kerala_endpoints_cli.py
```

The integer/rational bounds are checked against exhaustive small-cohort
contingency-table enumeration, including event-before-death allocations,
unknown endpoints, empty cohorts, contrasts and exact tipping thresholds.
The [observation model design](KERALA_OBSERVATION_MODEL.md) describes the next
source-native category/history/measurement adapter. Its diagnosis-dependent
OGTT omission must be represented before a likelihood is fitted. Clinical
hazards, remission, U.S. initialization, dietary effects and engine activation
remain unresolved. This analysis does not complete the v0.1 scientific gate.
