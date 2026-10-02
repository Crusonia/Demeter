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
counts, not six deaths. It also separates reasons for loss from the number
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
