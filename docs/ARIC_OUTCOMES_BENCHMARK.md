# ARIC public outcome panels

This benchmark preserves source-defined glycemic outcomes, deaths and selection
in an older U.S. community cohort. It advances the observation and calibration
work for the health slice. It supplies publication facts and conditional count
bookkeeping; clinical transition hazards and dietary effects remain unresolved.

The [paper](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2775594),
its currently advertised supplement, and the
[official PubMed record](https://pubmed.ncbi.nlm.nih.gov/33555311/) refer to the
same publication, DOI `10.1001/jamainternmed.2020.8774`. The intake pins the
supplement PDF and public NLM abstract XML separately. The
[correction](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2778331)
addresses incidence rates in Results, main Table 2 and supplement eTable 3, and
Key Points text. It does not explicitly replace eTable 2 counts. The adapter
extracts the pinned overall count rows and source definitions, not rates or
subgroup percentages. A malformed subgroup percentage is preserved as a source
limitation rather than silently repaired.

## Run the offline audit

From the repository folder, after [installation](GETTING_STARTED.md), these
commands work in PowerShell on Windows and in macOS/Linux terminals:

```bash
uv run demeter evidence aric-outcomes
uv run python scripts/verify_aric_outcomes.py
uv run demeter evidence aric-outcomes --output outputs/aric-outcomes.json
```

The default checks the frozen facts, complete scoped evidence records, source
receipts, transformations and derived report. It downloads nothing and reports
`raw_values_read: false`, `source_aggregates_reproduced: null`. Software integrity
does not mean clinical validation. Scientific gates remain closed.

For optional source replay, obtain both matching public files into an ignored
folder such as `data/raw/aric/`:

| Cache filename | Public source route |
| --- | --- |
| `rooney2021-corrected-supplement.pdf` | Discover the currently advertised Supplemental Content PDF at the publisher landing page. Use its producer-supplied link unchanged. |
| `rooney2021-pubmed-abstract.xml` | Official [NLM EUtils abstract XML](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=33555311&retmode=xml). |

```bash
uv run demeter evidence aric-outcomes --source-cache data/raw/aric
uv run python scripts/verify_aric_outcomes.py --source-cache data/raw/aric
```

Both sources must reproduce the frozen report exactly. One file is insufficient.
Changed public bytes require a reviewed new intake rather than silent repinning.
The PDF's cache filename is a local label; it does not independently establish
which corrections affected every table. The publisher's supplement link can
expire. Discover a fresh advertised link; do not save or manufacture signatures.
Stop at access denials or login requirements. The publisher HTML request was
denied during this intake; the public supplement and official abstract were
acquired through their separate documented routes. Future availability is not
guaranteed. No participant data or participant-access requests are involved.

## Count people once

Supplement eTable 1 partitions the original 3,412 people into 2,089 repeat-visit
attenders, 915 living nonattenders and 408 deaths before that visit. Supplement
eTable 2 reports 2,497 people under each assay definition. The original attendance
arithmetic and published source flow reconcile these sample sizes.

The A1c and fasting-glucose panels describe the same people. They are overlapping
observations, not independent studies. Each has two baseline rows and four
displayed outcome slots. The source reports normal glycemia and prediabetes;
neither category establishes general metabolic health or all insulin resistance.
Total diabetes combines assay thresholds, medication and physician diagnosis,
and is not a type-specific latent disease state or one biological event time.

| Assay / baseline source category | Selected baseline | Normal | Prediabetes | Displayed total diabetes | Displayed mortality |
| --- | ---: | ---: | ---: | ---: | ---: |
| A1c normal | 1,400 | 893 | 239 | 41 | 227 |
| A1c prediabetes | 1,097 | 148 | 645 | 97 | 207 |
| Fasting glucose normal | 1,035 | 731 | 80 | 26 | 198 |
| Fasting glucose prediabetes | 1,462 | 647 | 467 | 112 | 236 |

The adapter preserves A1c prediabetes 5.7–6.4%, fasting-glucose prediabetes
100–125 mg/dL, and total-diabetes assay thresholds of A1c ≥6.5% or fasting glucose
≥126 mg/dL, alongside medication or diagnosis routes. Lower glycemia does not
erase diagnosis history or establish sustained untreated remission. No OGTT
normality or engine-state mapping is inferred.

## Keep the missing baseline margin visible

The official abstract gives original baseline prediabetes counts of 1,490 for
A1c and 1,996 for fasting glucose. It gives 1,004 meeting both definitions and
2,482 meeting either. Inclusion/exclusion reconstructs the original joint assay
table; follow-up assay paths remain unpaired.

| Original baseline counts | Fasting glucose normal | Fasting glucose prediabetes |
| --- | ---: | ---: |
| A1c normal | 930 | 992 |
| A1c prediabetes | 486 | 1,004 |

Under the explicit source-reported subset interpretation, subtracting selected
baseline rows from original rows yields:

| Baseline source row | Original | Selected | Derived unrepresented baseline margin |
| --- | ---: | ---: | ---: |
| A1c normal | 1,922 | 1,400 | 522 |
| A1c prediabetes | 1,490 | 1,097 | 393 |
| Fasting glucose normal | 1,416 | 1,035 | 381 |
| Fasting glucose prediabetes | 1,996 | 1,462 | 534 |

These are **conditional source-margin reconstructions**, not observed follow-up
categories or independently verified missed-visit participant strata. No count
comes from rounding the supplement's percentages. The helper requires an
explicit subset declaration. A report retains that premise and the absence of
independent participant-membership verification. It supplies exact five-slot
fractions using original row denominators and four recorded-slot fractions using
selected row denominators. The unrepresented slot is null under the selected
denominator because it lies outside that population; unknown outcomes are not
treated as absent, dead, alive or wholly untraced.

## Preserve timing and event-history differences

The original attendance table reports 408 pre-visit deaths. The displayed outcome
panels and abstract report 434 mortality slots. Their difference of 26 does not
identify which attendance group those deaths belong to or resolve event clocks.
The abstract reports 156 cumulative incident diabetes events; the displayed
panels each contain 138 diabetes slots. The difference of 18 does not identify
18 diagnoses before death or any category priority rule. Parallel diagram boxes
and conserved counts cannot recover unreported event histories.

Baseline is 2011–2013 and the repeat visit is 2016–2017. Reported elapsed follow-up
has median 5.0 years, range 0.1–6.5. These are source descriptors. The adapter does
not substitute the median for every person's observation time, annualize counts,
fit competing clinical hazards, or treat the source partitions as a common-date
biological distribution. The two assay panels cannot reconstruct a joint
follow-up assay table or linked individual histories.

## Evidence, tests and next decision

The [frozen protocol](validation/aric-outcomes-intake-protocol-v1.json) was written
after selected source outcomes and diagrams had been inspected, and committed
before the new parser replay and reconstruction report. This is used-source
development, not preregistration, holdout validation or independent evaluation.
The [frozen report](validation/aric-outcomes-reconstruction-v1.json) separates
observed literals, derived counts, declared premises and unresolved interpretation.
Every selected substantive numeric input and derived static count is registered
under `aric_panel_*`, with status, units, provenance and uncertainty rationale.
Fixed publication literals supply no population sampling distribution.

`demeter.data.aric_outcomes.extract_aric_source_records` binds both byte snapshots,
article identity, exact PDF page/column structure, selected XML ancestry and
correction link. The raster flowchart is bound through native PDF image streams;
no OCR numerical extraction is claimed. The separate
`demeter.analysis.source_panel_reconstruction.reconstruct_source_panels` checks
mathematical accounting under caller-declared source identity. Independent small
integer allocations test conservation, denominators and overlap; adversarial
source tests reject ambiguous identity, moved sections, altered definitions and
reordered columns. The audit binds complete parameter/source/dataset records,
including provenance and uncertainty metadata, to a fixed checksum.

Full source text and figures remain in ignored caches because unrestricted
redistribution permission is not established. The repository distributes limited
attributed factual aggregates, original analysis and software, not participant
records or copyrighted full publications.

Design trace: I-01/I-05/I-07/I-11/I-12 → F-04/F-08 → T-05/T-08 in the
[design registers](design/README.md). The
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) remains open.
Before fitting a clinical process, resolve measurement/state mapping, selection,
event ordering and observation clocks, then specify identification, uncertainty
and independent evaluation. The existing synthetic likelihood kernels and annual
engine are separate. No dietary coefficient, mortality multiplier, national
initialization, clinical fit or scientific gate is activated here.
