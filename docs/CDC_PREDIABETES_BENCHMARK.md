# CDC prediabetes benchmark uncertainty

`observed_prediabetes_65_plus` now records the published confidence interval
alongside its unchanged point value. This resolves a missing-uncertainty metadata
gap. It does not calibrate the model's synthetic IR state, identify progression
or recovery, or validate a dietary effect. Scientific outputs remain blocked.

## Evidence-change record

| Field | Before | After |
| --- | --- | --- |
| Value / unit | 0.521 / fraction | Unchanged |
| Status / grade / role | observed / C / benchmark_only | Unchanged |
| Uncertainty | Missing | Published 95% CI, interval [0.468, 0.574] |
| Parameter bounds | Unspecified | Definitionally [0, 1] for a fraction |
| Source | [CDC summary](https://www.cdc.gov/diabetes/php/data-research/index.html), webpage updated September 16, 2026 | [Official report PDF](https://usdss.cdc.gov/diabetes/data/statsreport/National_Diabetes_Statsitics_Report.pdf), states updated March 11, 2026 |
| Source archive | No matching pinned report | Unmodified 3,232,798-byte PDF, retrieved October 1, 2026 |

CDC, *National Diabetes Statistics Report*, printed/physical page **23**:
“Estimated Crude Percentage of Prediabetes and Awareness…”; **Age Group ≥65**;
**Prediabetes**, first percentage/95% CI column. The published entry is
**52.1 (46.8–57.4)%**. The awareness column and age-adjusted tables are different
estimands. The PDF's stated update date, its export metadata and the later summary
webpage date are distinct; the archive receipt records actual retrieval.

This U.S. civilian noninstitutionalized NHANES survey estimate covers **August
2021–August 2023**. The table also names 2023 Census data; detailed methods use
Census population counts for estimated numbers, not a new Demeter denominator.
The CDC methods, pages **56–57**, classify people without diabetes as having
prediabetes with fasting plasma glucose **100 to <126 mg/dL OR A1C 5.7–6.4%**.
They exclude missing FPG/A1C values and pregnant women and distinguish crude from
age-adjusted estimates. Demeter transcribes the published result; it does not
re-estimate survey weights, sample denominators or variance from participant data.

The only numeric transformation is percentage ÷ 100. The CI is recorded as
`interval`, without converting it to an SE or imposing a normal/uniform sampling
distribution. It represents published sampling uncertainty, not measurement,
structural, transport or causal uncertainty. Cross-sectional prediabetes is not
all insulin resistance, an age-specific transition rate, or a dietary response.
No active equation, scenario assumption, population initializer or sampling input
uses this benchmark. No causal grade or national calibration is promoted.

## Offline reproduction

The [source manifest](../data/sources/cdc-prediabetes/2026-10-01/manifest.json)
pins the original URL/filename, retrieval, title, vintage, locator and SHA-256
`cd537b088973e44690e7a494a22b974f7bbd8a755210b8cf53238f13f1395bf1`.
The [rights inventory](../data/rights.json) and [notices](../data/NOTICE.md) retain
CDC attribution, free-source and non-endorsement conditions. The original PDF
stays separate from Demeter's extraction; no clinical participant records enter.

Run from the repository root on Windows PowerShell, macOS or Linux:

```text
uv run python scripts/verify_prediabetes_benchmark.py
uv run demeter data verify-store
uv run demeter data verify-packages --check-tracked --output outputs/package-audit.json
```

The verifier checks exact source bytes before parsing, requires the crude table
heading and one ≥65 row, selects the first estimate rather than awareness, and
matches point/interval, units, observed status and benchmark role to the registry.
Changed bytes, ambiguous rows or inconsistent registry values fail. Outputs go
to a fresh timestamped file in ignored `outputs/`; the source remains unchanged.
An explicit `--output` must name a new file: existing files and aliases are never
overwritten. Choose a fresh name when repeating the comparison below.
Omit `--check-tracked` for an
unpacked source distribution without Git.

To repeat the before/after comparison, first save the previous registry. This
Python command preserves its UTF-8 bytes on all three platforms:

```text
uv run python -c "import pathlib,subprocess; p=pathlib.Path('outputs/cdc-before.yaml'); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(subprocess.check_output(['git','show','1fc3d7825ce6b877b81920013d562eaaa8763734:evidence/parameters.yaml']))"
uv run python scripts/verify_prediabetes_benchmark.py --previous-registry outputs/cdc-before.yaml --output outputs/cdc-before-after.json
```

The [preserved result](validation/cdc-prediabetes-benchmark-before-after.json)
compares all canonical baseline, UPF and PreChronic outputs with only declared
evidence-hash paths excluded. Absolute and relative numeric differences are
**zero**. A two-draw, seed-42, two-year software regression retains identical
sampling inputs, draws and uncertainty outputs. Prevalence discrepancies and
historical mortality residuals stay unchanged; the clinical gates remain closed.
The registry hash and global missing-uncertainty audit change as expected.
Original historical protocols and receipts are preserved.

## Scoped assessment

**Software assessment:** automated source-byte/table checks, negative extraction
tests, complete before/after output comparison and repository checks; the PR
records the exact tested commit and suite results.

**Scientific assessment:** AI-assisted primary-source transcription and estimand
appraisal only; external expert review pending. The matching published point/CI
supports this narrow metadata correction. This is not independent human review
or clinical acceptance, and no competing causal effect is being selected.

**Merge disposition:** recorded in the implementation PR under maintainer
authority; merge is distinct from scientific acceptance.

**Scientific use:** benchmark only. Longitudinal observations, identifiable
clinical hazards, dietary causality and national transport remain unresolved in
[#57](https://github.com/Crusonia/Demeter/issues/57),
[#58](https://github.com/Crusonia/Demeter/issues/58) and the v0.1 acceptance gate.
