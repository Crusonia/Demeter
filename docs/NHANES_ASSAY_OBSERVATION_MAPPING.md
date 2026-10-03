# Paired assay observations and model states

A combined glycemic category can reproduce a published population table while
its two laboratory measurements place the same person in different threshold
bands. This audit tests the specific assumption that A1c and fasting plasma
glucose supply interchangeable, noiseless observed labels. It does not fit a
clinical state or decide which assay is correct.

The design trace is I-01/I-07/I-11/I-12 → F-08 → T-01/T-05/T-08 in the
[model-design registers](design/README.md). It complements the
[observation/state mapping contract](OBSERVATION_STATE_MAPPING.md) and the
[2021–2023 glycemic reconstruction](NHANES_2021_2023_GLYCEMIC.md).
Clinical initialization, transition fitting and the scientific release gate
remain closed.

## Run the audit offline

From the repository root after the [normal installation](GETTING_STARTED.md):

```powershell
uv run demeter evidence assay-mapping
uv run demeter evidence assay-mapping --output outputs/assay-mapping.json
uv run python scripts/verify_nhanes_assay_mapping.py
```

The commands work on Windows, macOS and Linux. The first prints a compact
summary and interpretation. The second saves aggregate estimates and joint
covariance. Use a new output filename for each run. Existing outputs and
aliases are never overwritten; output inside sources, evidence, documentation
or code is refused. No command downloads data or exports joined participant
records.

## What the comparison means

The same participant's released A1c and fasting glucose are classified
separately using the already registered cutoffs. Band names describe
measurements: `normoglycemic_range`, `prediabetes_range`, `diabetes_range`.
They do not identify Demeter's healthy, insulin-resistant or T2D stocks.

| A1c band / fasting glucose band | Normoglycemic range | Prediabetes range | Diabetes range |
| --- | --- | --- | --- |
| Normoglycemic range | Same observed band | Different observed bands | Different observed bands |
| Prediabetes range | Different observed bands | Same observed band | Different observed bands |
| Diabetes range | Different observed bands | Different observed bands | Same observed band |

The off-diagonal cells test deterministic label equivalence. Their frequencies
must use the actual paired observations. Multiplying separate A1c and glucose
margins would invent a pairing and can conceal disagreement even when the
margins are identical.

The tested denominator contains eligible adults with both valid assays and
the literal survey response `DIQ010 == 2` (No). This response is not proof of
complete negative lifetime diagnosis history. Yes, borderline and
uninterpretable responses remain separate in coverage and cannot enter this
denominator. A Yes response is retained even when a laboratory measurement
falls in a lower band; the audit cannot infer the reason.

One included discordant pair contradicts the literal implication that all
included pairs receive the same band. The report therefore uses
`contradicted_in_observed_sample`, `not_contradicted_in_observed_sample` or
`not_evaluable`. An empty domain is not evaluable. No observed discordance does
not establish clinical validity or universal agreement, and the result is not
a conventional population hypothesis test or an assay-accuracy ranking.

## Denominators, missingness and uncertainty

The eligible population retains two separate four-cell partitions: assay
availability (both, A1c only, glucose only, neither) and diagnosis response
(Yes, No, borderline, uninterpretable). Each partition closes separately;
the eight coordinates must not be added as one population partition. Missing,
nonfinite and nonpositive assays remain unavailable rather than agreement.

The paired No-response denominator has a nine-cell A1c-by-glucose partition.
Twelve adult age/sex domains are evaluated under both denominator families.
The fixed projection selects 204 coordinates from a 408-coordinate grid and
sums the six off-diagonal cells for each domain's discordance estimate. Joint
covariance retains dependence between assay cells, coverage, diagnosis
responses, denominator families and overlapping age/sex domains.

All positive-fasting-weight design rows remain in the variance calculation,
including those outside a particular adult subgroup. The audit reuses
WTSAF2YR, masked strata/PSUs, the current cycle, age/pregnancy rules and
confidence level from the admitted reconstruction. It does not substitute
phlebotomy or historical pooled weights. Full-design singleton strata are
refused. Empty estimates are unavailable; boundary estimates do not receive
fabricated intervals. Marginal logit-t intervals do not provide simultaneous
coverage of every coordinate. Expected covariance singularity is retained
without ridge repair or independent draws.

## Observed check

The first [frozen aggregate](validation/nhanes-assay-mapping-report-v1.json)
contains 2,418 eligible adult pairs in the literal No-response group, of which
969 receive different bands. The survey-weighted discordance estimate is 38.1%
(marginal 95% logit-t interval 35.2%–41.2%). These are Demeter's derived
observations under the declared denominator, not a published CDC estimate or
the fraction of all U.S. adults with discordance. The literal same-band
implication is contradicted in this observed group. The interval describes
survey sampling uncertainty, not latent diagnostic error or clinical validity.

## What remains unidentified

The observation pairs do not supply a gold-standard latent state, sensitivity,
specificity, confirmed diagnosis, diabetes type, medication history, onset,
remission or a dietary effect. Sampling covariance excludes measurement error,
missingness bias, pregnancy uncertainty and population/temporal transport.
Within-cycle GHB instrumentation changes are documented in the
[official codebook](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GHB_L.htm),
but no participant-specific instrument assignment is admitted, so disagreement
cannot be attributed to an instrument change.

The [protocol](validation/nhanes-assay-mapping-protocol-v1.json) fixes the
source identities, cutoffs, groups, coordinates, projections and interpretation
before these new diagnostic calculations. The source bytes, codebooks,
published results and earlier reconstruction were already inspected and used.
This is a used-source development freeze, not preregistration or an untouched
holdout. Every previous evidence definition and frozen reconstruction is
preserved. The [NCHS data-user agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html)
and [repository notices](../data/NOTICE.md) apply to the original public-use
components; only aggregate diagnostics and covariance are distributed here.
