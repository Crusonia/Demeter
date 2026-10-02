# Dataset reuse, citation and evidence packages

Demeter's MIT license covers its code and original documentation. It does not
relicense source data, articles, logos, or restricted records. The machine-readable
[rights inventory](rights.json) identifies all 53 archived artifacts and the
fetch-only sources by URL, publisher, vintage, retrieval time, checksum,
privacy class and citation. Its policies distinguish download, transformation
and redistribution conditions. These are packaging decisions; the linked source
terms control reuse.

[Evidence-package manifests](evidence-packages.json) connect sources to derived
artifacts, hashes, registry definitions, transformations, dependencies and reload
commands. These records describe reproducibility, not scientific acceptance.
Model outputs retain the existing validation-only boundary.

## Source-specific conditions

The [Malawi follow-up benchmark](../docs/MALAWI_FOLLOWUP_BENCHMARK.md) distributes
attributed publication aggregates and Demeter's derived bounds from Nakanga et al.
(2023), DOI `10.1371/journal.pgph.0001263`, under the article's
[CC-BY-4.0 notice](https://creativecommons.org/licenses/by/4.0/). Full publisher XML
is fetch-only by packaging choice. Underlying participant records remain
request-restricted and are neither acquired nor distributed. Extraction,
definitions and altered/derived calculations remain clearly identified.

The [Da Qing source audit](../docs/DA_QING_SOURCE_COVERAGE.md) distributes
attributed literal aggregate observations, an authored consistency audit and
receipts from Gong et al. (2016), DOI `10.2337/dc16-0429`. The primary article
records ADA educational, not-for-profit, unaltered-use conditions with citation.
Its full HTML, PDFs, figures and publisher layout remain fetch-only. The retained
facts are not fitted clinical parameters; the published count discrepancy and
repeated person-time/clinic dependence remain unresolved.

The [iPOP numerical preflight](../docs/IPOP_PREFLIGHT.md) uses the author-declared
public derivative accompanying [Zheng et al. (2022)](https://doi.org/10.1038/s41598-022-16326-9),
from the [producer repository](https://github.com/gmiaslab/TemporalMultiomicsDiabetes)
at commit `ba55996cb51a8bc4fbe9374633e9cb3223c6ea8c`. Original CC0 lineage and
the derivative repository's MIT code license remain distinct. Complete clinical
and metadata files are fetch-only; this repository distributes attributed
aggregate diagnostics, immutable selection protocols and receipts. Those
permissions certify neither participant identity nor clinical interpretation.

The [public linked-mortality package](../docs/LINKED_MORTALITY.md) includes
deidentified NHANES XPORT and fixed-width public-use records under the same NCHS
statistical-use restrictions below. Join only by the documented public survey
identifier. Never seek respondent identities. Follow-up through 2019 is public;
the 2022 restricted-use linkage is not redistributed or used here.

| Source family | Distributed material | Reuse basis and limits |
| --- | --- | --- |
| CDC/NCHS life tables, aggregates, healthspan PDF and UPF report | Unmodified agency artifacts; separate Demeter analyses | [CDC policy](https://www.cdc.gov/other/agencymaterials.html). Credit CDC; distinguish modified analyses from agency originals. Third-party content and marks have separate rights. |
| NHANES demographics, glycemic, risk and dietary files | Deidentified public-use XPORT; derived aggregates | [NCHS agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html). Statistical analysis/reporting only; no identification, linkage to identifiable data, or research to defeat disclosure protection. |
| Census PEP counts and ACS/PEP metadata | Public aggregate CSV and metadata JSON | [Census policy](https://www2.census.gov/foia/ds_policies/ds027.pdf), page 9. Employee works generally lack U.S. copyright protection; foreign and third-party rights may differ. No restricted microdata. |
| USDA ERS sweetener availability | Original CSV and derived historical series | [USDA policy](https://www.usda.gov/about-usda/policies-and-links). Attribute USDA ERS; third-party exceptions and marks remain separate. |
| NIDDK Look AHEAD summary | Original agency HTML; no downloaded remote images | [NIDDK policy](https://www.niddk.nih.gov/copyright). Credit NIDDK; third-party exceptions and logos remain separate. |
| ClinicalTrials.gov STEP 1 and STEP 4 | Historical sponsor-submitted JSON and aggregate extracts | [Registry terms](https://clinicaltrials.gov/about-site/terms-conditions). Attribute registry, processing date and modifications. No proprietary database claims or promotional use of extracted emails. International/third-party rights can apply. |
| Rodriguez et al. persistence study | Cited numeric extraction | The [article](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2829779) identifies CC-BY. Preserve author/journal attribution and [license notice](https://jamanetwork.com/pages/cc-by-license-permissions); underlying EHR records are not included. |
| Gregg et al. Look AHEAD remission | Limited factual extraction with DOI and caption locator | Numeric facts and Demeter's structure only; no full article, figure or publisher layout. [Facts differ from protected expression](https://www.copyright.gov/what-is-copyright/); this is not permission to expand the extraction into copyrighted material. |
| Rooney/ARIC and Koyama/LEADR | Registry estimates, intervals, citations and receipts | Full articles are fetch-only. ARIC has no redistribution permission recorded; LEADR is recorded as CC-BY but excluded by packaging choice. Article access is separate from patient-data access. |

CDC source materials are available at the original agency URLs **free of charge**.
Source use and links do not imply endorsement of Demeter or any product, service
or interpretation by CDC, HHS, NIH, NIDDK, NLM, Census, USDA or the U.S. Government.
Original source content stays unchanged; derived results are Demeter's analyses.
Do not reuse agency marks to suggest endorsement.

The [CDC prediabetes benchmark](../docs/CDC_PREDIABETES_BENCHMARK.md) adds the
unmodified National Diabetes Statistics Report, archived October 1, 2026. The PDF
states March 11, 2026 as its update date; its selected crude prevalence table uses
August 2021–August 2023 NHANES. This dated snapshot is available free at the
[official CDC URL](https://usdss.cdc.gov/diabetes/data/statsreport/National_Diabetes_Statsitics_Report.pdf).
Its agency marks are retained as part of the original report, not used as
Demeter branding or endorsement. No participant records are included.

ClinicalTrials.gov snapshots were retrieved on September 28, 2026. Both processing
versions are **2026-09-25**; last updates were posted **2021-11-19** for STEP 1 and
**2022-01-19** for STEP 4. Original JSON is unmodified. Demeter selects and normalizes
documented aggregate outcomes in `demeter.data.glp1.rebuild_glp1`.
These are historical research snapshots, not a current registry service. The terms
call for keeping distributed data current: consult [STEP 1](https://clinicaltrials.gov/study/NCT03548935)
and [STEP 4](https://clinicaltrials.gov/study/NCT03548987) before current-use
republication. Version updates separately instead of replacing historical bytes.

## Cite a reconstructable result

Include the Demeter version and Git commit, scenario and overrides, seed,
parameter-registry hash, and evidence-package ID. Cite original authors/publishers,
title, DOI or registry ID, exact URL/query/table locator, source vintage and
retrieval date. Retain source/derived hashes, transformation name and description
of changes. Cite sources as well as Demeter, preserve license notices, and separate
source observations from model assumptions. Do not cite synthetic outputs as
evidence of a health benefit.

For example, a STEP 1 benchmark citation includes `NCT03548935`, ClinicalTrials.gov,
the processing/posted/retrieval dates above, the source URL/hash from `rights.json`,
and `demeter.data.glp1.rebuild_glp1` with Demeter commit and output hash. This is a
registry extraction, not a new clinical finding.

## Reload and audit

From a repository checkout or unpacked source distribution:

```powershell
uv run demeter data verify-packages --output outputs/package-audit.json
uv run demeter data verify-packages --check-tracked --output outputs/package-audit.json
uv run python scripts/verify_source_archive.py --rebuild
uv run demeter data rebuild-nhanes
uv run demeter data rebuild-prechronic
uv run demeter data rebuild-healthspan
uv run demeter data rebuild-dietary
uv run demeter data rebuild-diet-response
uv run demeter data rebuild-glp1
```

The second command requires Git; omit `--check-tracked` for an unpacked source
distribution. The six named rebuild commands default to ignored `outputs/`
directories. The archive script rebuilds baseline/history in a temporary directory
and compares bytes. Dietary and PreChronic packages also need the glycemic store,
recorded as a dependency. Official JSON snapshots verify as-is, with no derived
engine dataset. The ontology exported by `demeter food-exposures` is an authored
definition contract, not downloaded observations.

The audit rejects missing rights/coverage, receipt mismatches, changed bytes,
unknown source/bundle files, invalid classifications and escaping paths. With
`--check-tracked`, it also rejects tracked caches, undeclared data-file types
elsewhere, and exact copies of fetch-only articles even when renamed. It neither
fetches data nor executes manifest commands.

## Fetch-only and restricted sources

Obtain matching authorized article bytes as `data/raw/clinical/aric.html` and
`data/raw/clinical/leadr.html`, then re-extract the clinical tables:

```powershell
uv run demeter evidence verify-sources --raw data/raw/clinical --output outputs/clinical-rebuilt.json
```

`--download` explicitly attempts the registered public URLs for missing files.
It does not bypass access controls or replace pins. Changed/unavailable sources
fail extraction; a changed snapshot requires reviewed revision. The output includes
re-extracted estimates/intervals with source and registry hashes and never changes
engine inputs.

On September 28, 2026, an explicit download attempt for both clinical sources
returned bytes different from the registered hashes. Those responses were rejected
and not cached. Fresh online re-extraction was therefore **not verified** in the
licensing/package audit; the prior source receipts and scientific blockers remain
unchanged. Matching authorized snapshots or a reviewed source revision are needed.

Without article access, committed estimates, intervals, locators and the prior
verification receipt remain inspectable. That is **not** fresh re-extraction.
Public NHANES and aggregate government packages provide offline learning and
pipeline alternatives; they cannot replace ARIC/LEADR longitudinal estimands.
Restricted NHANES, identifiable EHR data and private claims data are not included
or supported by the public package. Participant-level trial records are not included.
The optional [food-intake reproduction](../docs/FOOD_INTAKE_REPRODUCTION.md) accepts
a separately obtained public author archive in local ignored storage; its source
receipt and conservative fetch-only disposition are in the rights inventory.
Only Demeter-generated aggregates, method and code are distributed. An article's
open license does not make its underlying clinical records open.

## Distribution and contribution controls

The Chen et al. cohort is available under the dataset's CC0 dedication, verified
in Dryad and Zenodo metadata. Its large workbook remains fetch-only by packaging
choice; this is not a restricted-access requirement. Demeter distributes the
aggregate intake, protocol, source receipt and code. Article rights are separate.
The timing package adds aggregate diagnostics, a frozen protocol/amendment and
metadata receipts, with the same fetch-only workbook disposition. Article and
review-response PDFs are not distributed; factual locators and byte receipts
are retained. The later Sheng supplement contains the same workbook and adds
no independent participant records. See the [timing audit](../docs/CHEN_TIMING_AUDIT.md).

The separate PREDIMED-Reus original report (10.2337/dc10-1288) and correction
(10.2337/dc18-er10) are obtained through Europe PMC. Original XML records CC
BY-NC-ND 3.0; correction XML specifies educational, not-for-profit and unaltered
use with attribution. Demeter does not redistribute either full article. The
[Reus package](../docs/REUS_DIABETES_PATHWAY.md) contains factual estimates,
locators, receipts and original code only; these do not relicense publisher work.
The correction is separate from the unavailable multicenter Annals correction.
No participant data or reestimated clinical fit is distributed.

The DPP preservation package records four public documentation sources: the
primary report, protocol version 4.5, February 2008 release codebook and Version 9
catalog snapshot. Full content stays fetch-only; only factual definitions,
receipts, arbitrary synthetic fixtures/aggregates and MIT software are distributed.
The historical phrase "public release" does not grant current participant-record
access. No records have been requested or acquired and no clinical fit is supplied.
Source-version and timing uncertainties remain explicit in the
[DPP guide](../docs/DPP_OBSERVATION_ADAPTER.md).
See the [public evidence route](../docs/PUBLIC_EVIDENCE_ROADMAP.md).

Source distributions carry reviewed source bytes, manifests, transforms and
notices. Wheels carry small derived bundles and these notices/JSON inventories
under `demeter/data/notices/`. Raw public-use files come from the matching
repository/source distribution; inventory paths refer to that source tree.
Raw/processed/output caches are explicitly excluded from builds.

Whitehall II's [endpoint package](../docs/WHITEHALL_ENDPOINT.md) distributes a
limited attributed aggregate analysis from Vistisen et al. (2019), DOI
10.1007/s00125-019-4895-0, under the article's CC BY 4.0 attribution conditions.
Full article/ESM PDFs remain fetch-only. Published observations and Demeter's
conditional binomial interval are identified separately; this does not grant
access to controlled Whitehall participant records.

The [Geelong paired-label package](../docs/GEELONG_LABEL_OBSERVATIONS.md) includes
the unmodified Harland JW et al. (2025) publication XML,
[doi:10.1155/jdr/9926306](https://doi.org/10.1155/jdr/9926306), retrieved through
Europe PMC. Copyright © 2025 Jacob W. Harland et al. The literal article notice
permits use, distribution and reproduction under Creative Commons Attribution
with citation; it specifies no version, and Demeter does not invent one. Keep
the original copyright/license notice and attribution. Selected derived aggregate
facts retain their source citation and benchmark-only scope. Publication reuse
does not grant access to participant records. The recorded clinical-source
identity points to this reviewed archive, rather than authorizing any other
registry article to be redistributed.

The [Kerala trial intake](../docs/KERALA_SOURCE_COVERAGE.md) records the public
K-DPP dataset version 3, [DOI10.6084/m9.figshare.5661610.v3](https://doi.org/10.6084/m9.figshare.5661610.v3),
attributed to Sathish Thirunavukkarasu under its stated CC BY 4.0 license.
Both participant workbooks remain ignored and fetch-only. Authored receipts and
aggregate diagnostics omit participant keys, cluster keys, records and individual
assays. The release-metadata hash and two workbook hashes are separate pins.
Transient signed redirect queries are removed from public receipts and their
ignored originals are hash-linked. Trial publications/protocols stay fetch-only:
the 2018 trial article and 2023 follow-up protocol have separate CC BY attribution
conditions; this intake does not establish redistribution rights for the 2013
protocol. Study-ID consistency does not establish a producer identity crosswalk,
and undocumented numeric codes do not establish clinical or regimen meanings.

Before adding data, review contents, privacy classification, exact terms,
rights holder and attribution. Add reviewed rights, receipt, registry and package
records together. If rights or privacy are unresolved, exclude raw data and record
a permitted reproduction path. Never add identifiable health data or credentials.
Unlisted privacy classes fail validation. Checksums and an allowlist prevent
accidental additions/drift; they are **not** a PII detector or legal certification.
Content review remains required, including data embedded in prose or code.
