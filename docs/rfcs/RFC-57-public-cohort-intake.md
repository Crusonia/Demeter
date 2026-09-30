# RFC-57 extension: public Chen cohort intake

Date: September 30, 2026 UTC. Status: proposed scientific use; implementing a
descriptive source audit only. Parent: [RFC-57](RFC-57-longitudinal-identification.md).

The maintainer selected public sources. Institutional access is an optional future
route, not a prerequisite for the next contribution. Start with the Chen et al.
CC0 release identified in the [source appraisal](../LONGITUDINAL_SOURCE_APPRAISAL.md).
This advances input I-07 and health pathway P-02 without activating engine rates.

## Question and chronology

Can the released workbook reproduce the original cohort/event totals, and can we
reconcile its two diabetes fields with the study's glucose-or-diagnosis endpoint?
What follow-up timing and missingness must a later restricted analysis preserve?

This protocol is written after reading the article, metadata, workbook headers
and published results, before aggregating participant outcomes in this work.
It is a used-source reproduction protocol, not preregistration or an independent
holdout. No likelihood is fitted and no validation partition is chosen here.

## Locked analysis

The companion [JSON protocol](../validation/chen-public-intake-protocol-v1.json)
pins the workbook and analysis constants. Read the original workbook without
recalculation, follow-up links, or participant-level exports. Require the exact
source hash, sheet, headers and expected number of rows. Report missing fields,
duplicate identifiers, invalid codes and formulas explicitly. Do not drop records.

Reproduce the published total and sex counts and compare the binary column U
with the published event count. Preserve column T's blank, zero and one values
separately: its header defines one but does not define blanks. Compare column U
with the observed rule `final FPG >= 7.0 mmol/L OR column T == 1`; when neither
condition holds and T is blank, the rule remains unknown. Also report the
conditional reconstruction if blanks meant no reported diagnosis. Agreement
cannot independently prove that interpretation, endpoint timing or disease type.

Summarize follow-up years (minimum, quartiles, maximum, missing/invalid counts)
overall and separately by the recorded column U. Compare the overall median to
the published rounded median. Preserve discordance and failed checks. Report
baseline glucose above the study exclusion threshold and missing final glucose.
The source's participant IDs are used only to detect duplicates, never exported.

These are exact summaries of a fixed released file. They do not estimate a
population transition rate and have no sampling confidence intervals. Report
uncertainty as not estimated, with selection and measurement uncertainty unresolved.
Do not divide event fractions by median follow-up, treat a final low glucose as
sustained remission, or assign a U.S. weight to the selected Chinese cohort.

## Next scientific step

Use this intake to specify a restricted baseline/final glycemic observation model
and its identifiable estimands before fitting. It must retain interval observation,
diagnosis censoring, undocumented treatment/death histories and selection from
repeated health checks. Published aggregate transition studies are complementary
comparators; their probabilities are not interchangeable with instantaneous
hazards. The full #57 transition, competing-death and transport requirements remain.

## Validation and delivery

Test unknown diagnosis coding, missing glucose, ambiguous endpoint reconstruction,
invalid follow-up, duplicate IDs, formula rejection and source-hash mismatch with
synthetic fixtures. Reproduce the actual public release separately. Commit aggregate
JSON, exact provenance, analysis code and source terms. Keep the large workbook
fetch-only using its public pinned URL. Ordinary tests remain offline.
