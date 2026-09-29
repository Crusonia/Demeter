# PreChronic candidate definitions and model mechanics

Issue #8 adds an explicit, optional PreChronic stock. It is **not a newly
established clinical diagnosis**, and its transition rates are not calibrated.
The user-selected execution sequence builds and tests these mechanics before a
separate scientific calibration pass. Existing scenarios retain the three-state
`legacy` structure; the four-state scenarios remain validation-only.

The [observation-to-state audit](OBSERVATION_STATE_MAPPING.md) retains missing
records in a separate coverage denominator and shows diagnosis and age limitations.
Its crosswalk does not activate survey-derived initialization.

## Observable candidate definitions

The `nhanes_prechronic_candidates` dataset defines two research candidates among
NHANES 2017–March 2020 adults aged 20+. Both require normoglycemia under the
existing [glycemic reconstruction](NHANES_PREVALENCE.md), complete measurements,
and no reported diagnoses in the specified exclusion list. `risk_1` requires at
least one non-glycemic marker; `risk_2` requires at least two. These marker-count
choices are structural assumptions, not evidence-established clinical thresholds.

Markers use the definitions on the official
[NHLBI metabolic-syndrome diagnosis page](https://www.nhlbi.nih.gov/health/metabolic-syndrome/diagnosis):
waist above 40 inches for males or 35 for females; mean systolic pressure at least
130 or mean diastolic pressure at least 85 mmHg; HDL below 40/50 mg/dL; triglycerides
above 150 mg/dL. Waist uses exact inch-to-centimeter conversion. BP uses all three
oscillometric measurements and contributes one marker even if both means are
high. These rules do not constitute a metabolic-syndrome diagnosis. Population-
specific waist criteria, repeated clinical confirmation, fitness and direct
insulin-resistance measurements are not implemented.

The disjoint survey categories, in descending priority, are:

1. Glycemic diabetes of any type.
2. Glycemic prediabetes.
3. Other reported diagnosis: hypertension, high cholesterol, congestive heart
   failure, coronary heart disease, angina, heart attack, stroke or cancer.
4. PreChronic candidate under the selected non-glycemic marker count.
5. Lower measured risk: the remaining complete records, not proof of good health.

The diagnosis fields and missing codes are documented in the official
[BPQ](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_BPQ.htm) and
[MCQ](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_MCQ.htm) codebooks.
Unknown/refused responses and missing measurements are not treated as healthy.
Known pregnancy is excluded, within the age range for public pregnancy status.
Other chronic conditions and undiagnosed disease remain outside this definition.
Diagnosis access and treatment can affect classification; the exclusions do not
establish absence of every disease.

## Survey estimates, size and uncertainty

The transform joins ten public-use files by participant ID, checks the immutable
source bytes, and preserves all positive-weight strata/PSUs during domain
estimation. It uses fasting weights (`WTSAFPRP`) because the candidate definitions
require fasting glucose and triglycerides. See the official
[fasting-subsample guidance](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_TRIGLY.htm).
Age/sex domains follow the registered glycemic analysis (20+, 20–39, 40–59, 60+;
total, male, female). The all-adult domain overlaps the three age bands and must
not be added to them.

For complete-case domain indicator `D`, membership `Y`, and survey weight `w`,
the proportion is `sum(w D Y) / sum(w D)` and the represented count is
`sum(w D Y)`. Proportion variance uses Taylor ratio residuals and logit-t
intervals. Count variance uses within-stratum PSU weighted-total contrasts and
t intervals, truncated at zero. Empty/boundary cases have explicit unavailable
intervals. Counts are not inflated to replace missing records, and missing-weight
fractions travel with every domain.

In this pinned reconstruction, 3,211 of 3,769 eligible fasting-subsample adults
have complete records; 12.1% of eligible weight is excluded. The one-marker
candidate represents about 22.4 million people (sampling interval 18.1–26.8
million), versus 8.0 million (5.8–10.3 million) for two markers. These are
survey-weighted counts among classified respondents, not full-population clinical
PreChronic totals. Item-nonresponse bias, measurement error, missing diagnoses,
definition uncertainty and full NCHS reliability screening are outside those
sampling intervals. The two alternatives share the same observations.

Raw risk files and receipts live in `data/sources/nhanes-risk/2017-2020/`;
the original glycemic files remain in `data/sources/nhanes/2017-2020/`.
`prechronic_prevalence.json` and its checksum manifest are derived bundles shipped
in the wheel. Source files ship with Git and the source distribution. All numeric
definition choices, source links, status and uncertainty are in
`evidence/parameters.yaml`. The JSON is Demeter's reconstruction of official
XPORT files, not a CDC-issued PreChronic dataset.

## Four-state experiment

Scenarios select `health_structure: risk_1` or `risk_2`:

```text
healthy <-> prechronic <-> prediabetes -> t2d
    \          |              |          /
                  mortality
```

The state labels are synthetic proxies. NHANES all-type diabetes is not model
T2D, survey age/vintage differs from the engine, and a cross-section does not
identify transition hazards. The observed candidate counts therefore do not
initialize the model. Instead, a registered synthetic fraction of the original
healthy allocation is assigned to PreChronic; each definition has a separate
fixture and uncertainty range. The remaining original IR allocation becomes a
distinct prediabetes proxy. The lower-risk complement remains named `healthy`
for the healthspan interface, without asserting general health.

For source state `s`, competing exit hazards `lambda_sj` give total
`Lambda_s = sum_j lambda_sj` and survivor flows
`F_sj = N_surviving_s * (1-exp(-Lambda_s)) * lambda_sj/Lambda_s`.
All flows use the same pre-transition stocks; there is no within-step cascade.
Zero total hazard produces zero exits. Mortality occurs first, transitions at
year end, then aging. Existing source mortality reconstruction is retained with
the extra synthetic state ratio. This preserves people and the 100+ open group.

`h_to_pc_rate`, `pc_to_h_rate`, `pc_to_pd_rate`, `pd_to_pc_rate`,
`mortality_pc_ratio`, and `initial_pc_fraction_risk_1/risk_2` are new synthetic
registry fixtures. `ir_to_t2d_rate` and `mortality_ir_ratio` are reused as
synthetic prediabetes parameters. No empirical equivalence is claimed. The UPF
plumbing test multiplies the three forward hazards; reversal remains separate.
This response mapping, its lag and its reversibility are unvalidated hypotheses.

## Outputs and burden accounting

Standard simulate, compare, uncertainty, sensitivity and observability commands
support the four-state scenarios. Outputs include state stocks and flows,
age-specific period years, restricted cohort time, `prechronic_years`,
`restricted_prechronic_years` and cumulative new T2D entries. The
[healthspan timing contract](HEALTHSPAN.md) applies to all four states.

An additional tagged subcohort starts with people initially in PreChronic and
undergoes the same mortality and transitions. Its future T2D entries and share of
all future T2D entries quantify that initial cohort's contribution under the
specified assumptions. It can reverse and progress again, but is never copied or
counted twice. This is not a causal attributable fraction, a lifetime forecast,
or attribution to everyone who ever enters PreChronic. Mortality terminates
accrual; the simulation horizon limits the reported burden.

Uncertainty samples the active structure's parameters and preserves identical
draws for baseline/intervention. It includes PreChronic time and tagged-cohort
T2D burden. Different structures must be run separately: a paired intervention
comparison rejects mismatched definitions. Comparisons of `risk_1` and `risk_2`
also change synthetic allocation and are not clinical estimates of changing a
diagnostic threshold. Scientific mode remains blocked.

```powershell
uv run demeter data rebuild-prechronic --destination outputs/prechronic-rebuilt
uv run demeter evidence prechronic --output outputs/prechronic-evidence.json
uv run demeter simulate scenarios/prechronic_baseline.yaml --output outputs/prechronic-baseline.json
uv run demeter compare scenarios/prechronic_baseline.yaml scenarios/prechronic_reduce_upf_30.yaml
uv run demeter observe scenarios/prechronic_reduce_upf_30.yaml --draws 4 --samples 8 --destination outputs/prechronic-report
Start-Process .\outputs\prechronic-report\index.html
```

## Design trace and remaining science

The bounded health component of Q-03/RM-04 uses I-01/I-07/I-11/I-12,
F-01/F-04/F-08, and existing L-00 stock depletion from the
[design contracts](design/README.md). No prevention-finance or healthcare-cost
loop is implemented. `demeter.data.prechronic` supplies the observation mapping;
`demeter.health.structure` supplies the optional competing transitions;
`CohortTime` and `simulate` supply time and tagged burden.
`tests/test_prechronic.py` covers T-01 conservation, T-02 zero/extreme inputs,
T-03 finite horizons/open ages, T-05 alternative definitions and null changes,
and T-08 uncertainty/provenance. Annual operator splitting still needs a
time-step convergence appraisal before empirical use.

This closes the engineering state/interface work, not scientific acceptance:
candidate validity, transport of baseline observations, transition/mortality
identification, joint uncertainty and independent longitudinal holdouts remain
unresolved. They belong in the later calibration and validation pass. An
unverified effect must stay synthetic or unresolved rather than being promoted
to an observed causal parameter.
