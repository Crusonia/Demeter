# Kerala public trial: a finite route to linked observations

Assessment: October 2, 2026 UTC. This is a new primary source for the
clinical-observation work in #57 and the categorical intervention work in #58.
It is a source admission plan, not a fitted clinical result.

The Kerala Diabetes Prevention Program (K-DPP) is useful because it starts with
people selected for elevated diabetes risk, records normal glycemia as well as
prediabetes at entry, repeats assessments, and randomizes communities to a
peer-support lifestyle package or an advice booklet. It may therefore supply
linked changes between recorded categories. Those categories must retain their
source meaning: normal glycemia does not establish general metabolic health,
and a low measurement after diagnosis does not erase diabetes history.

## What has actually been acquired

The [primary trial publication](https://doi.org/10.1371/journal.pmed.1002575)
explicitly links its data to [the Figshare release](https://doi.org/10.6084/m9.figshare.5661610).
The live API identifies public **version 3**,
[10.6084/m9.figshare.5661610.v3](https://doi.org/10.6084/m9.figshare.5661610.v3),
with **CC BY 4.0** rights and two advertised workbooks. Both were acquired
without an account or agreement. Exact advertised byte sizes and both supplied
and computed MD5 fields match the downloaded files. SHA-256 pins are recorded
in the receipts. Raw participant workbooks remain ignored and are not committed.

Inspection has been restricted to sheet names, textual headers and structural
metadata. Both books have one `Sheet 1`, a title in row 1 and headers in row 2.
There is no separate or embedded dictionary, comment or metadata part describing
the clinical codes. No obvious direct-identifier header was found. That does not
establish that every cell is deidentified or that `participant_id` is the correct
linkage key. No participant identifier, assay value, record or quantitative
workbook outcome has been inspected or emitted.

The primary book contains candidate wide fields for baseline and two follow-ups:
`arms0/1/2`, `cluster0/1/2`, glucose and HbA1c measurements, ADA/WHO category
fields, medication fields and diabetes-incidence flags. The secondary book
contains candidate long fields with `participant_id`, `timepoint`, `arms`,
`cluster` and clinical measurements. These headers make actual joint person-wave
coverage plausible; they do not establish it.

## The follow-up problem is visible

The publication describes baseline, 12-month and 24-month assessments. It
diagnoses diabetes through annual OGTT testing or physician diagnosis plus
antidiabetic medication. People diagnosed at 12 months are still followed, but
their 24-month measurement uses fasting glucose alone rather than a full OGTT.
The missing two-hour test is therefore diagnosis-dependent. It cannot be treated
as an independently missed visit, a negative test or evidence of remission.

Figure 1, visually checked on PDF page 11, reports one control death and two
intervention deaths among losses at both follow-up horizons. These are cumulative
counts, not six deaths. Nondeath loss reasons are follow-up snapshots: some
reason counts decrease between waves. Do not subtract those snapshots to infer
interval losses or assume an absent participant or loss reason is absorbing.
The figure also separates reasons for loss from the number
analyzed for the primary outcome. No explicit death, contact, withdrawal, loss
reason or visit-date header appears in the released workbooks. Deaths therefore
remain known aggregate facts with unknown person, cluster and glycemic-state
allocation. We cannot infer that people with missing observations stayed alive
and unchanged, or assume independent censoring.

The [producer's 2023 follow-up protocol](https://doi.org/10.1186/s12889-023-15392-6)
documents unique K-DPP identification numbers separately from contact details
and uses Participant ID for linkage. It describes a later nine-year assessment.
It does not establish that the exact public version 3 fields use the same codes,
or that the downloaded files include nine-year data. Those distinctions stay
unresolved.

## The next finite intake

Before reading values, freeze the selected fields, source identities, required
code meanings, clocks, representation checks and stop conditions. The initial
protocol and header-row addendum preserve the actual inspection chronology. The
quantitative intake plan was written after publication outcomes and workbook
headers were read but before workbook values. This is used-source development,
not reserved independent validation.

The first value-level gate would inspect only the approved linkage, assignment,
wave, glycemic measurement/category, medication and incidence subset. It may use released opaque study keys privately in memory for representation
checks without claiming a producer crosswalk. It must distinguish unique wide person rows from
repeated wide rows, then verify matching long person-wave records. Numeric arm,
wave, category or medication codes cannot be assigned from expected published
counts or familiar conventions. Unresolved codes stop dependent interpretation; aggregate representation and
code-frequency appraisal may continue without guessing meanings.
Direct identifiers stop record analysis. No individual values or paths are
exported.

If those checks succeed, build aggregate joint histories of the source-defined
labels within assigned clusters and regimens. Keep all eligible released people,
paired observation completeness and recorded-event completeness separate.
Preserve unknown missing markers and post-diagnosis OGTT stopping. Reproduce
published denominators without trimming, collapsing or rescaling to make them
agree. Where same-cohort identity permits, deaths and reason-specific losses
enter compatible allocation bounds, never invented person-level events.

This advances actual linked source coverage. A possible later estimand is the
source-specific distribution of recorded glycemic histories under assigned
regimens, conditional on explicitly stated inclusion and ascertainment. It is
not an isolated dietary dose effect, latent clinical transition rate, national
parameter or life-expectancy prediction. Cluster and repeated-person dependence
remain explicit; individual independent-binomial intervals are unsupported.

## Model boundary

No clinical likelihood or fit is specified here. The intervention combines food,
activity, weight and other lifestyle goals; its offered category cannot become a
UPF dose coefficient. Source category definitions, confirmation/history,
medication roles, diagnosis-dependent testing, missingness alternatives,
death-allocation uncertainty and identification checks must precede any fit.
Scientific review and independent evaluation remain separate. Engine activation,
U.S. transport, clinical mortality and healthcare-savings claims are all blocked.

This intake feeds I-11/I-12 and F-08 in the design registers. It does not change
the v0.1 engine, its evidence parameters or the wider program architecture.

The active admission manifest is `validation/kerala-source-admission-v2.json`.
It retains the original frozen manifest through a parent hash and adds an
explicit artifact-path/redaction translation plus a follow-up snapshot
amendment. Original acquisition-related redirect query values stay ignored;
the historical sanitized coverage retains all clinical facts and limitations.
`uv run python scripts/verify_kerala_source_coverage.py` verifies these authored
relationships. Adding `--source-cache outputs/kerala-v3` also reproduces the
pinned headers and the original coverage's query-redaction projection. Neither
command reads participant values or verifies joint clinical coverage.


## Completed selected-field appraisal

The reproducible aggregate report is
[`validation/kerala-selected-source-representation-v1.json`](validation/kerala-selected-source-representation-v1.json).
The before-values admission was committed as `ea66036` before the first workbook
appraisal. Earlier used-source runs and the selected-string decoding repair are
recorded with immutable hashes; this is model development, not independent validation.

The primary workbook contains 1,007 unique typed opaque study keys. The secondary
workbook contains 3,021 rows for exactly those same keys: every key has one row
at each literal visit label `Baseline`, `12 months`, and `24 months`, with no
duplicate key/visit pair. Primary assignments are Control 507 and Intervention
500. Every linked long arm and opaque cluster agrees with its baseline wide
assignment across all 3,021 records. Cluster keys and participant keys stay private.

All 1,007 people contribute to 108 aggregate histories of source-native ADA
labels, assigned regimen and separate total recorded-diagnosis flag. Missing
labels remain in the histories. Baseline labels are NGT 312, IFG 579 and IGT 116;
these are observed released labels, not engine H/P/D states. At the next two
visits, 99 and 144 labels respectively are absent. A later lower glucose label
cannot erase a recorded diabetes diagnosis or establish remission.

The source total diagnosis flag is Yes 147, No 772 and absent 88: 919 available
endpoints reproduces the publication's endpoint denominator without dropping or
rescaling the released cohort. Among 88 source first-incidence Yes flags, all
88 later two-hour glucose cells are absent, while 82 later fasting glucose cells
are stored. This supports the publication's diagnosis-dependent OGTT stopping
rule. It does not supply individual death/loss histories or establish independent
censoring. The three reported cumulative deaths remain unlinked source facts;
nondeath loss reasons remain visit snapshots and are never differenced into
interval counts.

To repeat the original authoring appraisal with privately cached, pinned public
workbooks, use a new exclusive output filename:

```powershell
uv run python scripts/verify_kerala_source_coverage.py --source-cache outputs/kerala-v3 --appraise-selected-values --protocol-commit ea66036 --output outputs/kerala-v3/new-selected-appraisal.json
```

That command requires the original before-values commit in local Git history.
The committed aggregate artifact can be checked from its registered pin without
raw participant data or the authoring history. No clinical likelihood, biological
transition rates, independent-binomial intervals, U.S. transport, isolated diet
coefficient or engine activation is added by this report.

## Replay from a fresh public checkout

Verify the registered receipts, frozen aggregate report and exact appraisal code
without downloading records or retaining the original author's Git history:

```bash
uv run python scripts/verify_kerala_registered_coverage.py
```

For a public workbook replay, download both spreadsheets from the
[version 3 release](https://doi.org/10.6084/m9.figshare.5661610.v3) into
`outputs/kerala-public-replay`, keeping their original filenames:
`Primary outcome_K-DPP trial.xlsx` and `Secondary outcomes_K-DPP trial.xlsx`.
The files remain ignored and contain participant-level clinical records; the
replay emits only the authored aggregate diagnostics and verification flags.
These commands work in PowerShell, macOS Terminal and Linux shells:

```bash
uv run python scripts/verify_kerala_registered_coverage.py --source-cache outputs/kerala-public-replay --replay-aggregates --output outputs/kerala-public-replay/replay-v1.json
```

Use a new output filename for each receipt. This replay verifies the exact public
workbook bytes, headers and selected-field aggregate counts. It does not require
the author's earlier signed acquisition redirects or the before-values Git
commit, and it reports that omitted historical projection as unverified. The
authored report and its documented development chronology remain immutable.
All clinical fitting, engine activation and scientific release gates stay false.
