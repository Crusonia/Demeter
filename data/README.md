# Data in Demeter

Key datasets should travel with the code whenever their size and redistribution
terms permit. A fresh clone should let a reader inspect where an input came from
and reproduce the transformation. Demeter keeps source observations, derived
inputs, model assumptions, and simulation results distinct.

Start with [dataset reuse and citation notices](NOTICE.md), the per-source
[rights inventory](rights.json), and [evidence-package manifests](evidence-packages.json).

The [PREVIEW endpoint package](../docs/PREVIEW_ENDPOINT_AUDIT.md) contains factual
counts/estimates, source receipts, a frozen used-source analysis specification and
a descriptive missing-label audit. Four complete publication documents remain
fetch-only. The guide provides public-fetch and offline reproduction commands;
participant records have not been requested or acquired.

The [TOTUM63 adequacy package](../docs/TOTUM_SOURCE_ADEQUACY.md) checks a public
CC BY 4.0 workbook. The workbook and four source documents/metadata files remain
fetch-only here. Permitted aggregate coverage, frozen selection and historical
receipts are distributed. Actual collection dates, unique participant pairing and
complete clinical histories remain unverified; no individual values are exported.

The [DPP preservation package](../docs/DPP_OBSERVATION_ADAPTER.md) contains public
documentation receipts, a frozen field contract and synthetic aggregate checks.
Full documents are fetch-only and participant records are request-only. Its
offline command imports no participant data and does not fit a clinical model.
The separate [source coverage appraisal](../docs/DPP_SOURCE_COVERAGE.md) adds
factual form/dictionary locators and receipts; its additional documents are
fetch-only and are outside the adapter's original four-document byte check.
The package audit validates their typed metadata against documentation-rights
records. Optional `--documentation-raw outputs/dpp-appraisal` checks all 15 local
documents; offline byte checks remain explicitly not requested.
`uv run demeter data verify-packages --check-tracked` audits their coverage and
receipt consistency, checks source/bundle bytes, and rejects undeclared tracked
data and caches. The notices also explain fetch-only articles and wheel contents.

## What is included today

| Dataset | Repository location | What it supports |
| --- | --- | --- |
| CDC/NCHS U.S. life tables, 2022–2024, total/male/female | `sources/baseline/2026-09-26/nchs_*.xlsx` | Observed mortality schedules and life-table checks. |
| U.S. Census single-age/sex resident counts, Vintage 2025 | `sources/baseline/2026-09-26/census_2025.csv` | Population initialization for 2022–2024. |
| CDC/NCHS historical mortality aggregates | `sources/historical/2026-09-26/nchs_life_expectancy.csv` | Historical benchmarks; no age-specific causal dietary estimate. |
| CDC/NHIS diagnosed-diabetes series | `sources/historical/2026-09-26/nhis_diabetes.csv` | Historical observations with a 2019 comparability break; diagnosed diabetes is not all T2D. |
| USDA ERS caloric-sweetener availability | `sources/historical/2026-09-26/sweeteners.csv` | Food-system context; availability is not individual intake or UPF exposure. |

These 13 original files total about 1 MB. They match the source hashes already
pinned in the model. Folder dates identify the pinned retrieval snapshot, not
the years of the observations. Each source's publisher, URL, vintage, original
retrieval time, and checksum are in the linked manifests. The
[archive receipt](sources/archive.json) records the size, checksum, manifest link,
and independent archive retrieval time of each committed copy.

## Source to result

The [linked mortality store](../docs/LINKED_MORTALITY.md) adds five public-use
CDC/NCHS files for the 2011–2012 development cycle and mortality through 2019.
`uv run demeter data rebuild-linked-mortality` reconstructs linkage coverage and
aggregate event counts offline. These are feasibility diagnostics, not fitted
health hazards or an independent validation pass.

The [frozen mortality evaluation](../docs/MORTALITY_VALIDATION.md) adds five original
2013–2014 public-use files and an aggregate prediction receipt. Its protocol and
four fitted models were committed before outcome intake. Run
`uv run python scripts/validate_mortality_holdout.py` to reproduce offline. This
descriptive temporal check does not identify causal state or dietary effects.

The [GLP-1 store](../docs/GLP1.md) contains official ClinicalTrials.gov STEP 1 and
STEP 4 JSON responses and a separately labeled persistence-study extraction.
`uv run demeter data rebuild-glp1` reconstructs their benchmark bundle offline.
The trial records preserve available-case SDs and adjusted-effect confidence
intervals separately. No benchmark values silently replace treatment parameters.

Additional catalogued stores include NHANES glycemic and PreChronic reference
data, the NCHS healthspan arithmetic example, official JSON snapshots, and the
[dietary reference bundle](../docs/FOOD_EXPOSURES.md). The dietary store adds
eight original files (about 67 MB): seven public-use XPORT files and one government
HTML report. Four nutrient survey cycles and published UPF history reconstruct
into 249 source-linked observations. The smaller derived JSON ships in the wheel;
the original files remain in Git for offline reloading. `data/catalog.json`
lists every store, source manifest, role and reload command; `demeter data
verify-store` verifies them all. The original 13-file archive script below
continues to cover only the baseline and historical CSV/XLSX stores.

```text
data/sources/<family>/<snapshot>/   immutable, reviewed source bytes in Git
                  |
src/demeter/data/ingest.py         baseline transform
src/demeter/data/historical.py     historical transform
                  |
src/demeter/data/bundled/          small model-ready bundles + manifests in Git/wheel
                  |
evidence/parameters.yaml + scenarios/ + model equations
                  |
outputs/                         local generated results; ignored by Git
```

`data/raw/` is an ignored download/work cache, not the canonical archive.
`data/processed/` is reserved for ignored intermediate outputs. A local file in
either directory is not automatically a reviewed source. Ordinary runs use the
bundled inputs and do not download data.

- [Baseline manifest](../src/demeter/data/bundled/manifest.json)
- [Historical manifest](../src/demeter/data/bundled/historical_manifest.json)
- [Evidence registry and definitions](../evidence/README.md)
- [Historical series contract](../docs/HISTORICAL_BACKTESTS.md)

## Verify and reproduce without changing the repository

```text
uv run python scripts/verify_source_archive.py
uv run python scripts/verify_source_archive.py --rebuild
```

The first command verifies every archived artifact against its existing source
manifest and archive receipt. The second also rebuilds both bundles into a
temporary directory and compares their bytes with the committed bundles. Missing
files, changed bytes, or different outputs fail the check. It does not fetch data
or overwrite committed artifacts. CI repeats this on all supported platforms.

The existing `demeter data rebuild` and `rebuild-history` commands remain available
for intentional pipeline maintenance; they write bundled artifacts. Their default
raw locations are caches. See the manifests and `--help` before updating sources.
Do not regenerate a checksum merely to silence a failed verification.

## Adding and updating datasets

Open an issue or PR linking the dataset to a model question. Include:

1. Exact source URL, publisher, title, release/vintage, retrieval date, and byte
   checksum; record original filenames or an explicit local-name mapping.
2. Redistribution terms and attribution, population, geography, period, units,
   missing/suppressed values, uncertainty, and definition/comparability breaks.
3. The immutable raw snapshot, a reproducible transformation, its output schema,
   and relevant evidence-registry entries. Identify whether it drives the model
   or is only a benchmark or future candidate.
4. Checks for source corruption and transform correctness; a before/after report
   explaining changed model inputs and outputs, including unresolved differences.

Add a new versioned snapshot for a changed source. Preserve prior source bytes
and identify which model version uses each vintage. Commit small, permitted key
datasets directly, together with the metadata and transform. For a large source,
agree on a versioned release artifact or appropriate public data archive first;
keep its durable locator, checksum, reuse terms, fetch procedure, and a small test
fixture in Git. Do not silently replace a dataset with an unversioned web link or
make novices manage Git LFS for the current small sources.

Restricted or nonredistributable sources are exceptions: commit only permitted
metadata/extractions and document how authorized researchers can obtain them.
Never upload identifiable health records, credentials, or full articles without
redistribution rights. Clinical source receipts currently live in the evidence
registry; full publisher articles are not included in this archive.

The [food-intake reproduction](../docs/FOOD_INTAKE_REPRODUCTION.md) is another
explicit exception: the author's public trial ZIP has no recorded redistribution
license. The repository contains the pinned receipt, method, Python transform
and aggregate results; raw participant records and author code stay in ignored
local storage. Its command accepts a separately obtained archive and works offline.

The [Reus evidence package](../docs/REUS_DIABETES_PATHWAY.md) distributes small
factual HR/CI extracts, frozen analysis records, source receipts, compatibility
checks and original code. Both full XML articles stay fetch-only under their
publisher permissions in ignored local storage. It contains no participant
records. Downloading articles is optional and separate from offline simulation
and synthetic compatibility checks.

## Source credit and terms

The dietary timing store retains an official NIDDK HTML summary and a small
explicitly labeled factual JSON extraction from a published trial figure caption.
It supports a [historical structural challenge](../docs/DIET_DYNAMICS.md), not
national UPF calibration. Publisher article text is not redistributed. Reload
with `uv run demeter data rebuild-diet-response`; the catalog identifies its
`historical_challenge_only` role and receipts.

The archived baseline and historical files are from CDC/NCHS, the U.S. Census
Bureau, CDC's U.S. Diabetes Surveillance System/NHIS, and USDA ERS, as attributed
per file in the manifests. These government data retain their source terms;
Demeter's MIT software license does not relicense third-party material.

Use of these materials and links does not imply endorsement of Demeter, its
interpretations, or any product by CDC, HHS, Census, USDA, or the U.S. Government.
See [CDC's reuse policy](https://www.cdc.gov/other/agencymaterials.html),
[Census research/public-access policy](https://www2.census.gov/foia/ds_policies/ds027.pdf),
and [USDA's policies](https://www.usda.gov/about-usda/policies-and-links).

Source availability is not causal validation. Keep data definitions separate
from the modeled quantities, and leave unsupported mappings explicitly unresolved.

## NHANES and official JSON additions

The [machine-readable catalog](catalog.json) covers all 51 archived source files, including
four deidentified NHANES 2017-March 2020 XPORT files and four official JSON
snapshots and the NCHS healthspan method PDF. The original baseline and historical
archives above remain canonical.

Six additional NHANES risk/diagnosis files live in
`sources/nhanes-risk/2017-2020/` with official links, checksums and terms.
`uv run demeter data rebuild-prechronic` rebuilds candidate counts and age/sex
distributions offline. [PreChronic methods](../docs/PRECHRONIC.md) explain the
alternative definitions, survey uncertainty and missing-data limitations.

- [NHANES source manifest](sources/nhanes/2017-2020/manifest.json) links the four
  public-use CDC files, their codebooks, dates, and SHA-256 hashes.
- [Official JSON snapshot manifest](sources/official-json/2026-09-27/manifest.json)
  distinguishes CDC data observations from Census discovery metadata.
- [Derived prevalence JSON](../src/demeter/data/bundled/nhanes_prevalence.json) and
  [reconstruction methods](../docs/NHANES_PREVALENCE.md) describe the survey
  classifications, weights, uncertainty and remaining engine-state mismatch.

Reload and verify without changing committed files:

```powershell
uv run demeter data verify-store
uv run demeter data rebuild-nhanes --destination outputs/nhanes-rebuilt
uv run demeter data rebuild-healthspan --destination outputs/healthspan-rebuilt
uv run demeter evidence population --output outputs/population-evidence.json
```

The source store is included in the repository and source distribution. Built
wheels contain the derived bundles. NHANES public-use records are subject to the
[NCHS data-use terms](https://www.cdc.gov/nchs/policy/data-user-agreement.html):
statistical reporting and analysis, without identification or linkage to
individually identifiable records. Source data terms remain distinct from the
software license.

## Official JSON APIs

The [healthspan source manifest](sources/healthspan/nchs-2001/manifest.json) pins
the official NCHS PDF used for the Sullivan arithmetic check. Its extracted JSON
is a Demeter transform, not an official JSON publication. It is stored separately
from engine inputs and reproduces offline; see [healthspan methods](../docs/HEALTHSPAN.md).

- [CDC mortality and life expectancy JSON](https://data.cdc.gov/resource/w9j2-ggv5.json?%24where=race%3D%27All%20Races%27&%24limit=5000&%24order=year%2Csex): historical aggregate observations, not single-age life tables.
- [CDC diabetes JSON sample](https://data.cdc.gov/resource/c9xs-vhst.json?%24limit=1): NHIS diagnosed diabetes; not all diabetes, laboratory prediabetes, or specifically T2D. The catalog retains the complete filtered query used for the snapshot.
- [Census ACS population query](https://api.census.gov/data/2024/acs/acs1?get=NAME%2CB01001_001E&for=us%3A%2A): JSON data service, but the unauthenticated check on September 27, 2026 redirected to `missing_key.html`. Append your Census API key privately; never commit it.
- [Census ACS age/sex JSON metadata](https://api.census.gov/data/2024/acs/acs1/groups/B01001.json) and [PEP 2023 JSON metadata](https://api.census.gov/data/2023/pep/charv/variables.json): verified public metadata, not population observations.

The ACS survey and PEP population estimates have different definitions and vintages.
Neither linked API is silently substituted for the engine's Census Vintage 2025
single-age CSV. NHANES publishes the source microdata here as SAS XPORT; Demeter's
derived JSON is explicitly identified as our reconstruction, not an official CDC JSON release.
