# Data in Demeter

Key datasets should travel with the code whenever their size and redistribution
terms permit. A fresh clone should let a reader inspect where an input came from
and reproduce the transformation. Demeter keeps source observations, derived
inputs, model assumptions, and simulation results distinct.

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

## Source credit and terms

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
