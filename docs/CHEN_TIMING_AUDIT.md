# Chen follow-up timing audit

The public cohort audit is complete; its timing discrepancies remain unresolved.
The released data can support source-specific descriptive benchmarks. They do
not yet support fitting or activating progression/reversal hazards. This advances
[#57](https://github.com/Crusonia/Demeter/issues/57) while compatible public
observations are sought. Other public-source work can continue.

## What was frozen before calculation

The [timing protocol](validation/chen-followup-timing-protocol-v1.json) was
committed as `4ba3208` before the new duration aggregations. The
[arithmetic amendment](validation/chen-followup-timing-amendment-1.json) was
committed as `15049be` before those calculations too. Published results and the
earlier intake discrepancy were already known: this is not preregistration or
an independent holdout. The original intake protocol and result are preserved.

The [design RFC](rfcs/RFC-57-chen-timing-and-observation.md) separates the timing
diagnostic from a future observation likelihood. All analysis inputs live in
the `chen_followup_timing_audit` evidence record. The numerical day-grid tolerance
is a synthetic software diagnostic, not a clinical tolerance or effect.

## What the released durations show

The [aggregate receipt](validation/issue-57-chen-timing.json) retains every
released record and separates endpoint groups, missing values and denominators.
The comparison assumes ordinary rounding to the publication's displayed
precision; it does not assume an undocumented alternative follow-up estimator.

| Quantity | Published | Released-data arithmetic | Disposition |
| --- | --- | --- | --- |
| Total follow-up, person-years | 660,191 | 661,468.19 | Disagreement retained |
| Median follow-up, years | 3.1 | 2.989733 | Disagreement retained |
| Arithmetic mean, years | Not explicitly reported as a mean | 3.122593 | Rounds to 3.1; explanatory hypothesis only |
| Crude events per 1,000 person-years | 6.17 | 6.310205 | Disagreement retained |
| Crude rate from the paper's own event count and person-years | 6.17 | 6.322413 | Internal arithmetic disagreement retained |

The median is the middle duration after sorting; the mean divides total duration
by the number of records. Their difference matters here. A mean that rounds to
the published median is not an author correction and does not resolve the other
disagreements. These are source checks, not estimates of annual clinical hazards.

Multiplying the released durations by 365.25 places all records within the frozen
numerical tolerance of whole days. That is consistent with one day-to-year
conversion, but actual dates were not released and cannot be reconstructed as
verified observations. One duration exceeds the conservative 2010-through-2016
calendar bound under each checked conversion. It remains in the audit. No rows
are trimmed, durations rescaled or missing information imputed.

The article's two-year repeated-visit eligibility rule is also reported as a
diagnostic. It does not establish that every diagnosis-stopped duration must be
at least two years. The source locators and this clarification are recorded in
the [primary-source receipts](validation/chen-timing-source-receipts.json).

## What can be estimated next

Exact released-file summaries and the recorded endpoint fraction are descriptive
benchmarks. A glycemic-category analysis would first need a separate frozen,
source-supported definition and threshold protocol. Neither a low final glucose
value nor a blank diagnosis cell establishes diabetes remission.

The source describes follow-up stopping at diagnosis or the final visit. A
scheduled-panel transition probability alone does not account for that stopping
process. Exact events, interval-detected events and administrative final visits
require different observation contributions; the actual release does not settle
which is appropriate. The likelihood remains **unresolved**, fitting and engine
activation remain disabled, and deaths, treatment and post-diabetes histories
are not invented. The selected Chinese screening cohort does not identify U.S.
or national PreChronic rates.

[Sheng et al. (2024)](https://doi.org/10.3389/fendo.2024.1388751) provides a
progression/regression comparator using this same Chen cohort. Its supplementary
workbook is byte-identical to the pinned release; it adds no independent visit or
death histories. Its category boundaries, selection and stopping assumptions need
alignment before reproducing a descriptive comparator. It cannot serve as an
independent validation set.

## Reproduce on Windows, macOS or Linux

After the [public-cohort download instructions](PUBLIC_EVIDENCE_ROADMAP.md), run
the same command from the repository root on any supported platform:

```text
uv run demeter evidence public-cohort-timing --workbook data/raw/clinical/chen2018.xlsx --output outputs/chen-timing.json
```

The command verifies the pinned source, protocol, amendment and intake definition
before opening the workbook. It writes aggregate JSON and currently exits **1**
because the retained source checks fail. That expected source-audit outcome is
separate from passing software tests. It never downloads data implicitly,
recalculates formulas or exports participant rows.

## Scientific disposition

Primary article locators are Study design (`s2a`), Ascertainment (`s2b`), Results
(`s3`) and Table 2's Crude rate row. The public reviewer response, physical page
4, records unavailable death information. The reviewed version listing and
supplements did not identify a timing correction; this bounded search is not
proof that none exists. Original data are CC0; article and supplement rights are
separate, and their full contents are not redistributed.

Automated Codex critique informed this audit. External scientific review remains
pending. No engine equations, hazards, evidence grades or uncertainty
distributions are changed. #57 and the v0.1 scientific acceptance gates remain
open; this audit does not establish clinical, economic or investment findings.
