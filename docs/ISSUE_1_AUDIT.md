# Issue #1 audit and resume contract

Audited base: `ca943606d67492dac02fb23ae19644422c7ef7ac` (`main`).
Issue #1 and milestone #27 remain **incomplete**. This branch advances the evidence
audit; it is not a completed scientific v0.1 release.

## Existing work preserved

- The existing 49 tests and Ruff passed before edits.
- Single-age cohorts, mortality calibration, conserving transitions, life tables,
  scenario parsing, paired uncertainty, Sobol analysis, and CLI surfaces already exist.
- Bundled data are NCHS 2022–2024 mortality schedules and Census Vintage 2025 counts.
- The historical check is a 2022→2023 mortality-persistence benchmark; it does not
  validate diet, metabolic transitions, or healthspan.
- Active metabolic parameters remain synthetic. Published cross-sectional total
  diabetes benchmarks are not silently relabeled as T2D.

`POST_V0_1_ROADMAP.md` and `BACKTESTING_STRATEGY.md` were absent from audited main.
Their exact existing versions were recovered from `origin/docs/post-v01-roadmap`
at commit `2b4b178` without replacing their content or starting later modules.

## Changes on this branch

- Add six source-checked clinical estimates from corrected ARIC and LEADR tables.
- Preserve source URLs, DOIs, corrections, licenses, raw checksums, retrieval times,
  confidence intervals, estimands, source populations, and extraction transforms.
- Add CLI appraisal and offline/source-download verification with explicit failures.
- Reject use of a benchmark as a required engine input. Candidates do not alter
  model trajectories or enter Monte Carlo/Sobol parameter sampling.
- Preserve confidence intervals as intervals, not invented distributions.
- Test corrupt/missing sources, extraction drift, accidental parameter promotion,
  corrected-source metadata, and unchanged simulation behavior.

## Exact scientific work still required

| Acceptance gate | Required next work | Why current evidence is insufficient |
| --- | --- | --- |
| Baseline state definition and prevalence | Define compatible glycemic states; estimate age/sex state shares using appropriate survey weights and uncertainty; distinguish T2D and other diabetes | Existing adult fractions are synthetic; total diabetes is not T2D and normoglycemia is not overall metabolic health |
| Progression and reversal | Estimate compatible age/state hazards, including competing deaths and regression, from longitudinal evidence; document transport beyond source populations | The extracted clinical rates differ in population and estimand; they do not identify national current-state hazards |
| State mortality | Establish defensible age/state excess hazards and confounding assumptions | Aggregate mortality calibration identifies the mixture, not its state decomposition |
| Food effect and dose | Choose an evidenced exposure scale and endpoint; model uncertainty, transport, and overlapping exposures | The active relative-UPF effect is synthetic and modifies two unidentified transitions |
| Lag | Obtain temporal response evidence consistent with the food intervention and state model | A chosen relaxation constant is not evidence of a dietary effect delay |
| Historical health holdout | Predeclare fitting and holdout windows, reconstruct comparable observations, evaluate health outcomes and mortality, and report omitted shocks | The existing frozen-mortality comparison has no dietary or metabolic prediction |

The papers inspected do not resolve these matching and identification problems.
This is **not** a claim that relevant evidence does not exist. Candidate sources
and verified estimates should accelerate the next extraction/calibration pass.
Do not close #1, merge this as a completed issue, start unsupported downstream
mechanisms, or mark any #27 checkbox on the strength of this evidence audit alone.

## Verification and next action

Run the full verification commands in README, both new evidence commands, and
`git diff --check`. `validate --scientific-required` must still exit 1.
The source extraction receipt is `docs/validation/issue-1-clinical-sources.json`.
The execution checkpoint records final test/CI results and the PR state.

Resume on `codex/issue-1-evidence-gates`. Begin with the state-definition and
age/sex prevalence gate above. Preserve one PR for #1; add defensible evidence,
calibration, and holdout results before considering its acceptance criteria met.
The next milestone issue after #1 is #6.
