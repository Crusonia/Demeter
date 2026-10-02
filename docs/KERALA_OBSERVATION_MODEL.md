# Kerala source-specific observation model

Status: design input, October 2, 2026. No likelihood fit, clinical-state mapping,
parameter promotion or engine activation. This feeds **I-11/I-12 → F-08 →
T-05/T-08** in the [design registers](design/README.md) and advances the
observation-design work for [#57](https://github.com/Crusonia/Demeter/issues/57).
It preserves the [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md)
and v0.1 boundary.

Implementation status: the [private nominal adapter, public aggregate audit and
synthetic discrete likelihood evaluator](KERALA_NOMINAL_OBSERVATIONS.md) now
implement the preservation and software-validation portions below. The empirical
observation channel, clinical mapping and calibration remain unresolved.

The public K-DPP release supports a linked, source-native observation process.
It does not identify latent healthy/prediabetes/T2D hazards. All source outcomes
and intake results have already been used; subsequent work is model development,
not independent evaluation.

## Supported observations and unresolved meanings

| Input | Supported representation | Limits on interpretation |
| --- | --- | --- |
| Literal ADA categories | Preserve `NGT`, `IFG`, `IGT`, `diabetes`, and unavailable labels at literal `Baseline`, `12 months`, `24 months` visits. | NGT is not general metabolic health; IFG and IGT are distinct source labels. Do not equate them with engine H/P/D states or silently reclassify assays. The released category algorithm lacks a separate producer dictionary. |
| Recorded incidence | Preserve literal Yes/No/absent values of `tot_diab_incidence`, `tot_diab_incidence1`, `tot_diab_incidence2`, separately from measured categories. | The total flag's 147 Yes observations match the paper's endpoint total. The two suffix flags' cumulative-versus-interval semantics require private consistency checks; their names alone do not establish first-event intervals. A later lower glucose label cannot erase positive recorded history. |
| Medication | `diabdrugs_1` and `diabdrugs_2` contain literal Yes/No and uninterpreted text markers. Baseline-looking `diabdrugs_10`/`diabdrugs_20` are entirely absent in the selected appraisal. | No verified drug identity, dose, start/stop date, continuous use, medication-free duration or complete baseline history. A Yes flag alone does not establish physician diagnosis; a No flag does not establish treatment-free remission. |
| Conditional OGTT omission | The completed trial describes no 24-month OGTT following **12-month OGTT diagnosis**, while fasting glucose is still measured. | Distinguish a test omitted by protocol from missed visits, other unavailable measurements and unknown causes. Do not apply this rule automatically to every early incidence flag or clinical diagnosis. |
| Death and loss | Preserve the publication's cumulative death counts and its nondeath reason snapshots as unlinked arm-level constraints. | No participant/cluster/category death linkage, exact death times or individual loss reasons. Do not mark unknowns alive, sum repeated death counts, difference nondeath snapshots into interval losses, or assume independent censoring. |

These statements refer to the pinned
[public release v3](https://doi.org/10.6084/m9.figshare.5661610.v3), the
[completed 2018 trial](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1002575)
(Methods: Procedures, Outcomes, Statistical analysis; Results: Incidence;
Figure 1), and the registered
[selected-field report](validation/kerala-selected-source-representation-v2.json).
The report exposes no labeled multiwave trajectory tuples; linked records and
history grouping remain private. See [source coverage](KERALA_SOURCE_COVERAGE.md)
for exact bytes, header locators, permissions and the used-source chronology.

## Protocol and completed-trial differences

The [2013 protocol](https://link.springer.com/article/10.1186/1471-2458-13-1035)
specified incident diabetes from a single OGTT and proposed Cox analysis. The
completed 2018 paper instead defines the endpoint through annual OGTT or
physician diagnosis **with** antidiabetic medication. It reports cluster GEE
for cumulative incidence because systematic assessments occurred at the two
annual visits. Neither document establishes exact biological onset or a
repeat-test confirmation requirement for this endpoint.

The 2018 Procedures section states: “an OGTT was not performed at 24 months;
instead, FPG alone was measured.” Its preceding sentence identifies the trigger
as OGTT diagnosis at 12 months. The release has 87 literal `diabetes` labels in
`glycemiaADA1` and 88 Yes flags in `tot_diab_incidence1`; all 88 have unavailable
later two-hour glucose cells. These are different marginals. Their difference
does not identify a participant's diagnosis route or justify broadening the
documented omission rule. Check their joint consistency privately.

Eligibility also excluded baseline OGTT diabetes while retaining a subgroup
with diabetes-range HbA1c. Preserve that source selection; do not repair it by
inventing a homogeneous diabetes-free biological entry state.

## Observation-design sequence

1. Add a source-specific in-memory observation adapter with a **nominal visit
   index**, literal category, source incidence flags, assay availability and
   medication flags. Keep exact collection/contact/confirmation times unknown.
   Do not convert nominal visits into randomization-relative exact days or call
   a single study OGTT a separately confirmed diagnosis.
2. Audit the three incidence flags jointly: positive-flag overlap, total-versus-
   suffix agreement, contradictory labels, and explicit unknown combinations.
   Retain every enrolled key and positive history. Independently check the
   OGTT-based omission trigger, clinical-route uncertainty, and fasting-versus-
   two-hour availability. Export only approved scalar consistency counts,
   one-way marginals and unlabeled coverage summaries.
3. Specify a **discrete nominal-visit observed-data model** before estimation.
   Its candidate factorization includes assay availability conditional on prior
   recorded information, observed source labels conditional on availability,
   and recorded diagnosis ascertainment. Keep assigned regimen fixed and retain
   cluster and repeated-person dependence. Protocol-omitted tests have their
   declared observation operator; unexplained missingness needs alternatives,
   bounds or an explicit observation model, never an automatic all-ones mask.
4. Evaluate a declared candidate likelihood with synthetic checks before any
   source-specific fit. Compare available source endpoints and measurement
   patterns at their documented resolution. Treat any conditional analysis of
   measured people as that selected estimand, not an assigned-regimen causal
   effect or an estimate of missing categories. Death/allocation bounds remain
   a separate documented analysis, not fitted mortality coefficients.

The existing
[clinical preservation objects](../src/demeter/data/clinical_observations.py)
require explicit relative-day clocks and confirmation observations; they must
not force those meanings onto this release. The
[linked-path evaluator](../src/demeter/analysis/longitudinal_likelihood.py)
offers declared continuous-time software kernels with retained diagnosis
history, but supplies neither this ascertainment process nor an informative
missingness model. Its first-entry modes cannot silently substitute for detected
study diagnoses, and `exp(Q t)` is not the annual engine operator.

The implemented adapter and synthetic evaluator advance actual source
compatibility for #57. They do not establish remission, latent-state hazards,
an isolated dietary dose effect, U.S. transport, mortality improvement or
healthcare savings. Independent scientific review and release acceptance remain
separate.
