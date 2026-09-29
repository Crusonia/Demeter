# Reproducing one food-intake contrast

Demeter reproduces the primary daily-intake contrast from the author archive for
[Hall et al. (2019)](https://pubmed.ncbi.nlm.nih.gov/31105044/). This advances
[#58](https://github.com/Crusonia/Demeter/issues/58): it makes one upstream food
comparison inspectable, while leaving the disease-transition link unresolved.

The question is specific: how did mean daily energy intake differ when the same
adult volunteers were offered the trial's ultra-processed and unprocessed menus
in an inpatient setting? This is a contrast between whole menu regimens. It is
not a continuous effect of UPF share or an isolated effect of processing.

## Result and interpretation

The [aggregate report](validation/issue-58-food-intake.json) records 20 complete
participant pairs, with 14 daily observations per diet: 560 daily records in
total. The paired PROC-minus-UNPROC difference is **507.73 kcal/day**, with a
standard error of **105.73 kcal/day** and a two-sided 95% t interval of
**286.43–729.03 kcal/day**. Mean and standard error reproduce the published
integer values of 508 and 106. The interval is calculated here, not presented as
a quoted published confidence interval. Days are repeated observations;
the paired interval has 19 degrees of freedom.

The report also shows both randomized sequences separately and an additive
common-period sensitivity. Its diet contrast is 507.73 kcal/day, with a 95%
interval of 279.57–735.90. This sensitivity cannot distinguish differential
carryover from treatment effects. Neither interval includes uncertainty about
national transport, measurement error, long-term adherence or disease mechanisms.

This is **numerical reproduction on used data**, not independent validation.
The published result and archive structure were known when the
[analysis plan](validation/food-intake-reproduction-protocol-v1.json) was recorded
in [7c5edce](https://github.com/Crusonia/Demeter/commit/7c5edce4cbed09bc47ec60e8cb27135244568fd6),
before Demeter computed the new estimate. All participants remain in the analysis;
missing, duplicated or inconsistent pairs fail rather than being silently omitted.

## Run it on Windows, macOS or Linux

Start with the normal [installation instructions](GETTING_STARTED.md). The author
archive is intentionally separate from the repository: the public OSF node did
not state a redistribution license when inspected. Raw data and author code stay
in ignored local storage. Only receipts, Demeter code and aggregate results ship.

Download the pinned **ADLDataSAScode2.zip** from the
[author's data repository](https://osf.io/khqug/), or use these commands. Preserve
an existing download; do not overwrite it to silence a checksum failure.

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force data/raw/clinical | Out-Null
$intakeArchive = "data/raw/clinical/hall2019-intake.zip"
if (-not (Test-Path -LiteralPath $intakeArchive)) {
    Invoke-WebRequest "https://osf.io/download/fsqb7/" -OutFile $intakeArchive
}
uv run demeter evidence food-intake --archive $intakeArchive --output outputs/food-intake.json
```

macOS or Linux:

```bash
mkdir -p data/raw/clinical
test -e data/raw/clinical/hall2019-intake.zip || curl --fail --location \
  https://osf.io/download/fsqb7/ --output data/raw/clinical/hall2019-intake.zip
uv run demeter evidence food-intake \
  --archive data/raw/clinical/hall2019-intake.zip --output outputs/food-intake.json
```

The command itself is offline. It verifies the recorded protocol, archive,
daily-intake member and author-code hashes, reads the SAS data with Python,
and writes aggregate UTF-8/LF JSON. It does not execute SAS, extract archive files
to disk, contact a server or export participant identifiers and individual results.
Only the required daily-intake table is decoded.

The expected ZIP SHA-256 is
`c941c1cd33abb0cf17fb982aaec0fb23da034c94e5b86ec949a0e73704a6fbb8`.
The source receipt identifies OSF file `6012eb8bdd222502a058d064`, version 1,
uploaded January 28, 2021. A new archive version needs a reviewed intake; changing
a checksum alone is not a correction. Users without matching source bytes can
inspect the committed aggregate report but cannot reproduce the raw-data transform.

## Corrections and source limits

Both correction identifiers are retained: [2019](https://pubmed.ncbi.nlm.nih.gov/31269427/)
and [2020](https://pubmed.ncbi.nlm.nih.gov/33027677/). The
[accessible PMC notice](https://pmc.ncbi.nlm.nih.gov/articles/PMC7959109/)
states that the meal-level diet-label error did not affect total daily intake.
The author's [January 2021 response, pp. 1 and 9](https://retractionwatch.com/wp-content/uploads/2021/01/Response-to-Blog-post-1-update-1.pdf)
links that error to the October 2020 notice and acknowledges the then-pending
archive update. The selected archive follows that response. Their chronology
differs; the plan preserves this discrepancy and records that the 2020 publisher
body was unavailable. We do not invent a separate adjustment to daily intake.

The archive's `Period` field identifies diet (`PROC`/`UNPROC`), not chronological
period. `DietOrder` and calendar day identify sequence. Demeter verifies their
consistency. It does not reconstruct daily measurements from the separate meal
files or appraise the archive's macronutrient and body-composition endpoints.

## What changes in the model

`food_intake_reproduction` records the method and all analysis constants in the
evidence registry. `hall2019_menu_intake_difference` is an estimated,
**benchmark-only** parameter, with its paired interval and limited applicability.
It is excluded from active model inputs and sampling. The
[before/after receipt](validation/issue-58-food-intake-before-after.json) confirms
unchanged numerical outputs for baseline, UPF reduction and PreChronic scenarios.

The [design RFC](rfcs/RFC-58-food-pathway-identification.md) still requires a
validated food-to-disease bridge. Intake is not a metabolic transition rate;
the whole-menu contrast does not identify a dose conversion or a clinical lag.
No engine equation, active coefficient, scientific-release gate, healthcare-cost
forecast or investment conclusion is changed.

Software checks cover paired arithmetic against a hand calculation, period
sensitivity, invalid input rejection, source checksums, canonical CLI output,
registered-estimate drift and aggregate reconciliation. CI uses synthetic records
and the saved aggregate receipt; it does not claim to rerun the excluded raw ZIP.
The actual pinned author ZIP was reproduced locally. Independent scientific
assessment and maintainer disposition remain pending.
