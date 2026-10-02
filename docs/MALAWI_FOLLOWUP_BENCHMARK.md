# Malawi follow-up: categories, deaths and missing people

Demeter can reproduce a small public aggregate benchmark from
[Nakanga et al. (2023), PLOS Global Public Health](https://doi.org/10.1371/journal.pgph.0001263).
This supplies a baseline impaired-fasting-glucose (IFG) cohort and its reported
follow-up dispositions. It does not calibrate the U.S. health engine.

The publication's reported partition is:

| Disposition | People | Evidence status |
| --- | ---: | --- |
| Baseline source IFG cohort | 389 | Observed published count |
| Traced | 190 | Observed published count |
| Assessed alive | 175 | Observed published count |
| Confirmed dead among traced | 15 | Observed published count; not a complete death total |
| Untraced | 199 | Derived as 389 − 190; not classified as alive or dead |
| Assessed source NGT | 106 | Observed Table 1 category count |
| Assessed source IFG | 24 | Observed Table 1 category count |
| Assessed source DM | 45 | Observed Table 1 category count |

The three assessed categories sum to 175; assessed, confirmed dead and untraced
sum to the original 389. A person cannot disappear from the accounting because
their follow-up is missing. These counts and the selected definition/timing
literals are registered as `malawi_*` parameters with `benchmark_only` roles.
Grade C describes this limited observational use, including incomplete tracing
and inconsistent classification thresholds; it is separate from effect size.

## Run it

From a configured repository checkout on Windows, macOS or Linux:

```text
uv run demeter evidence malawi-cohort --output outputs/malawi-cohort.json
uv run python scripts/verify_malawi_cohort.py
```

The default is offline. It checks the frozen protocol/report, registered facts,
transform bytes and derived bounds. It reports `raw_values_read: false` and
`source_aggregates_reproduced: null`; checking committed metadata is different
from re-extracting the publication.

The complete scoped registry records are checksum-bound: values, units, status,
citation, locator, population, geography, time period, transformations, uncertainty
and source receipt. A custom `--evidence` file may change unrelated records; any
change to these frozen Malawi records fails the audit, even when its value is
unchanged. An approved amendment needs a new reviewed record pin.

To repeat extraction, obtain the public publisher XML from the source URL in
`evidence/parameters.yaml`, retain the exact bytes as
`data/raw/malawi/nakanga2023-manuscript.xml`, and run:

```text
uv run demeter evidence malawi-cohort --raw data/raw/malawi/nakanga2023-manuscript.xml --output outputs/malawi-source-replay.json
uv run python scripts/verify_malawi_cohort.py --raw data/raw/malawi/nakanga2023-manuscript.xml
```

These commands never download or replace sources and refuse an existing output.
Changed publisher bytes fail the pin; retain the original and propose a new
version rather than resealing this historical receipt. No participant records
are needed. Follow [the setup guide](GETTING_STARTED.md) for a first installation.

## Read the result

The observed 45/175 DM fraction describes reassessed people. It is not the
original cohort's diabetes risk. The bounds preserve a single unknown allocation:

```text
x_NGT + x_IFG + x_DM + x_death = 199
each x is a nonnegative integer
```

Hold the recorded categories and confirmed deaths fixed, and allow each untraced
person exactly one compatible source-category/death disposition. The original-
cohort DM-category fraction ranges from 45/389 to 244/389; possible recorded death
dispositions range from 15/389 to 214/389. These are finite-cohort information
bounds, not confidence intervals, probabilities assigned to completions or
annual transition rates. The unknown allocation is an analyst sensitivity
representation, not observed data or an assumption of independent missingness.

For the category fraction among alive completions, the denominator varies from
175 to 374. The DM coordinate extrema are 45/374 and 244/374: different completions
attain each endpoint. The generic calculation retains exact rational values and
handles empty survivor denominators explicitly. Coordinate maxima for NGT, IFG,
DM and death cannot all occur together; every full completion must conserve the
original cohort. The report retains that joint constraint.

These dispositions describe mixed source follow-up ascertainment times, including
possible completions for untraced people. They are not a population's alive/dead
or glycemic distribution at one common elapsed time. A category assessed earlier
does not establish survival through the end of the follow-up period. The bounds
also do not reconstruct diagnosis before death, first onset or subsequent events.

## Preserve the source's definitions and discrepancies

Baseline IFG requires FPG ≥6.1 and <7.0 mmol/L, no prior diabetes diagnosis and no
diabetes medication. Follow-up IFG uses ≥6.0 and <7.0; source NGT uses <6.0. The
lower cutoff changes. NGT here is a fasting-only source label: no OGTT normality,
general metabolic health or sustained untreated remission is established.

Follow-up DM allows a diagnosis since baseline **or** current diabetes medication
**or** FPG ≥7.0 mmol/L. It is not a purely contemporaneous glucose measurement,
nor a verified type-2-specific latent state. It cannot be placed directly into
Demeter's three health stocks.

Baseline runs from 2013–2016 and follow-up from 2018–2019. Published follow-up
median 4.2 years and IQR 3.4–4.7 describe variable elapsed times, not individual
event clocks or one horizon. Abstract person-years are 714; Results person-years
are 714.9. Both literals are preserved as a source discrepancy. Neither is
selected, corrected or used to annualize the category counts.

The article reports differences between reassessed people and those lost to
follow-up. The [official Data Compass record](https://datacompass.lshtm.ac.uk/id/eprint/961/)
was checked on October 2, 2026: its underlying cross-sectional data remain
request-restricted under a data-sharing agreement. The paper's planned
anonymization does not establish present unrestricted access. Demeter uses only
public publication aggregates; no restricted records are acquired or requested.

## Reproducibility and next design decision

The [frozen protocol](validation/malawi-cohort-intake-protocol-v1.json) pins primary
article and table identity, exact selected XML ancestry, normalized paragraph
hashes, category columns, captures, corroborating counts and closed scientific
gates. Published counts and definitions were inspected before the protocol. This
is used-source development, not preregistration or independent validation.
The [frozen report](validation/malawi-cohort-ascertainment-v1.json) retains observed
literals, derived residual, explicit discrepancies and coupled bounds.

`demeter.data.malawi_cohort.extract_malawi_cohort` performs source extraction;
`demeter.analysis.followup_category_bounds.followup_category_bounds` performs the
separate mathematical sensitivity calculation. Tests reject mismatched source
identity, ambiguous locators, altered definitions, moved category columns and
invalid cohort partitions, and compare the bounds with exhaustive small-cohort
completions. Package/CI checks run offline; optional raw replay is separate.

Design trace: I-01/I-05/I-07/I-11/I-12 → F-04/F-08 → T-05/T-08 in the
[design registers](design/README.md) and
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md).
This benchmark makes loss and ascertainment constraints explicit. It does not
identify a complete transition matrix, state mortality hazards or a dietary
causal effect. Combining its one source IFG row with other cohorts requires an
explicit measurement, selection, timing and population-transport model; stacking
counts as though they were independent rows would not supply that model.

The [existing scientific gaps](EVIDENCE_GAPS.md) remain open. No likelihood fit,
sampling interval, national transport, clinical initialization, annual hazard,
dietary scenario effect or scientific gate is activated by this intake.
