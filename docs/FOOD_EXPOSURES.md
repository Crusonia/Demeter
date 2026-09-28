# Food exposures and dietary state

Issue #24 implements a small exposure contract and reproducible U.S. references.
It does not calibrate dietary effects. The active health response still uses the
synthetic UPF coefficient and lag in `evidence/parameters.yaml`; scientific mode
remains blocked. Full calibration is a separate, stepwise validation task.

## Canonical definitions and units

`datasets.food_exposure_ontology` in the evidence registry is the canonical
definition table, validated by `ExposureOntology` / `ExposureDefinition` in
`src/demeter/nutrition/exposures.py`. `Scenario.diet` uses typed `DietaryChange`
records. `demeter food-exposures` emits the contract, evidence, supported relative
envelope and explicit transition mapping.

| Exposure | Kind and unit | Current use |
| --- | --- | --- |
| UPF | Nova food category; percent of dietary energy | Observed adult means/SEs; absolute targets normalize to the existing synthetic response |
| Fiber | Nutrient; g/day | Observed intake distributions; context only |
| Total energy | Energy; kcal/day | Observed intake distributions; no energy-balance equation |
| Total sugars | Nutrient; g/day | Context only; **not added sugars** |
| Protein | Nutrient amount; g/day | Context only; **not protein quality** |
| Saturated fat | Nutrient; g/day | Context only; **not an overall fat-quality index** |
| Fruit/vegetables | Food category; proposed cup-equivalents/day | Unresolved inclusion rules and food-pattern conversion; rejected in absolute scenarios |
| Added sugars | Nutrient; g/day | Unresolved food-pattern conversion and effect |
| Refined carbohydrate | Food category | Operational definition/load units unresolved |
| Protein quality, fat quality | Quality indices | Index definition and units unresolved |
| Omega-3 | Nutrient; g/day | ALA/EPA/DHA and supplement inclusion unresolved |
| Nutrient density | Deferred quality index | Definition and units unresolved |

Nonnegative intake and UPF's 0–100% bounds are definitional constraints, not
study-supported dose ranges. Empirical min/max and quantiles describe reported
days. The registered UPF relative envelope is a **synthetic software envelope**;
outside it `allow_extrapolation: true` is required. This never permits an
impossible percentage or enables scientific mode. No empirical causal exposure
range is claimed for any of these variables.

## Sources, storage and historical reconstruction

The immutable store `data/sources/dietary/2026-09-27/` retains seven original
CDC XPORT files and the NCHS published UPF HTML tables. Its manifest contains
official download/codebook URLs, byte hashes, retrieval times and data-use terms.
The transform also reuses the existing pinned `P_DEMO.xpt` demographics file.
Nothing downloads during reconstruction. Raw publisher bytes are never rewritten.

- [NCHS Data Brief 536](https://www.cdc.gov/nchs/products/databriefs/db536.htm):
  extract nine unique adult observations from Tables 1, 2 and 5. These include
  UPF mean energy shares and standard errors in 2013–2014, 2015–2016, 2017–2018
  and August 2021–August 2023, plus latest adult sex and age groups. The latest
  total appears twice and must agree. These are published observations; an
  individual UPF distribution is unavailable here, not invented from the SE.
- Day-one nutrient totals and demographics for
  [2005–2006](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DR1TOT_D.htm),
  [2013–2014](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/DR1TOT_H.htm),
  [2017–March 2020](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DR1TOT.htm),
  and [August 2021–August 2023](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/DR1TOT_L.htm):
  reconstruct 240 age/sex/nutrient cells. Use `WTDRD1` or the pre-pandemic
  `WTDRD1PP`, reliable recalls, and complete records for the five nutrients.
  Domain means use Taylor-linearized sampling SEs and t intervals; weighted
  quantiles describe **single reported days**, not usual individual intake.

For domain `D`, weights `w`, and reported intake `x`,
`mean = sum_D(w*x)/sum_D(w)`. The linearized PSU contribution is the sum of
`w*(x-mean)/sum_D(w)` in that PSU, with zero contribution outside the domain.
Within each stratum the variance contribution is `m/(m-1)` times the sum of
squared centered PSU contributions. Retain out-of-domain PSUs. Degrees of freedom
are domain PSUs minus domain strata. Intervals are absent for empty/degenerate
domains, not fabricated; singleton strata fail. Nonnegative interval truncation
and the registered confidence/quantile levels are explicit in the transform.

The resulting 249-cell JSON bundle and manifest ship with the Python package.
The bundle retains source population, period, sex/age domain, units, status,
grade, sampling uncertainty, missing-weight fraction for reconstructed nutrients,
and descriptive distributions. Numeric derived output is stored at 12 significant
digits, using the existing cross-platform storage policy; original bytes and
published UPF numbers are preserved.

These cycles are analyzed separately. The 2017–2018 UPF table is **not** the
2017–March 2020 nutrient sample. UPF adults are 19+; nutrient domains are 20+.
Pregnant adults are not excluded from the dietary reconstruction. The first
recall changed from in-person to telephone in 2021–2023; that comparability break
is flagged. Survey sampling intervals omit recall bias and food-code/measurement
changes. None of these data identify longitudinal disease transitions.

These particular official releases are XPORT and HTML, not JSON APIs. Our derived
JSON is labeled as such. The existing [catalog](../data/catalog.json) also links
official CDC health JSON and Census population JSON services with access notes.

```bash
uv run demeter data verify-store
uv run demeter data rebuild-dietary --destination outputs/dietary-rebuilt
uv run demeter evidence dietary --output outputs/dietary-evidence.json
uv run demeter food-exposures --output outputs/food-exposures.json
```

## Scenario changes and overlap protection

Existing relative `exposures: {upf: 0.7}` files retain their behavior. New files
can specify an absolute target, its exact unit, the observed reference period,
and its application role. Do not specify the same exposure in both forms.

```yaml
name: dietary_upf_30
mode: validation
diet:
  upf:
    target: 37.1
    unit: percent_energy
    reference_period: '2021_2023'
    role: model_effect
```

For the all-sex published adult reference of 53%, this target represents a
15.9 percentage-point reduction and normalizes to `37.1/53 = 0.7` relative
exposure. It is an illustrative scenario assumption, not a recommended intake.
Sex-specific scenarios require matching sex-specific references; unavailable
period/sex references fail instead of silently substituting a national mean.
The engine applies the scenario uniformly above its separately registered adult
threshold; age/population/vintage transport remains an explicit limitation.

The existing equation remains `target_log_effect = beta * (relative_upf - 1)`
with the registered exponential lag. It modifies H→IR and IR→T2D progression in
the legacy model, or H→PreChronic, PreChronic→prediabetes and prediabetes→T2D in
the optional four-state models. These mappings are synthetic and await appraisal.

An observed nutrient target must use `role: context_only` (see
`scenarios/dietary_context.yaml`). Its reference, target, absolute change and
unapplied role are retained in simulation/comparison metadata. It changes no
health hazard. This is an unimplemented causal link, **not an estimated zero
effect**. Unresolved definitions fail even in context mode; missing units or
application roles fail. Registry edits cannot activate a second effect without
an explicit implementation.

The ontology records overlapping food-category, nutrient and composite variables.
UPF overlaps with sugar, fiber, energy and other food attributes; adding their
putative effects independently would risk counting the same dietary change more
than once. The bundle includes descriptive weighted same-day nutrient correlation
matrices. They are not causal relationships or parameter-covariance estimates;
no joint UPF/nutrient correlation is inferred from aggregate UPF tables. The
engine therefore accepts only one active dietary pathway. It does not infer a
mass-balanced substitution, food basket, adherence, or calorie deficit.

Uncertainty runs reset absolute targets as well as legacy relative exposure for
their paired no-change baseline. They sample the existing synthetic effect/lag
parameters, holding the observational reference means fixed. Reference SEs remain
visible; an SE is not silently turned into a causal sampling distribution.

```bash
uv run demeter simulate scenarios/dietary_upf_30.yaml --output outputs/dietary-upf.json
uv run demeter compare scenarios/baseline.yaml scenarios/dietary_upf_30.yaml
uv run demeter uncertainty scenarios/dietary_upf_30.yaml --draws 64 --seed 42
```

## Design trace and validation boundary

Q-03 / RM-04 → the exposure-to-health portion of P-02 (upstream of the future
L-08/L-10/L-11 financing/behavior loops) → I-05/I-07/I-11/I-12 → F-04/F-08.
No loop is closed by this change, and no externality or financial account is added.
Registry keys `food_exposure_ontology`, `dietary_baselines`,
`beta_upf_progression`, `diet_lag_years`, and `upf_min/max_multiplier` trace to
`nutrition/exposures.py`, `data/dietary.py`, `schema.py`, and `model.py`.

`tests/test_dietary.py` covers T-01 units; T-02 absent/extreme/invalid inputs;
T-05 context-only null effects and legacy/four-state equivalence; and T-08 source
integrity, survey arithmetic, historical definitions, uncertainty pairing, and
rejection of unsupported effects. Same-source reconstruction is reproducibility
evidence, not an independent health holdout or calibrated dietary effect.
