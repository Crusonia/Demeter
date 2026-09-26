# Basic Food → Healthspan Dynamics: execution checkpoint

Milestone **not complete**. No issue was closed and no PR was merged in this run.

## Repository state

- Base main: `ca943606d67492dac02fb23ae19644422c7ef7ac`.
- Branch: `codex/issue-1-evidence-gates`.
- PR: [#29](https://github.com/Crusonia/Demeter/pull/29), draft, partial #1 work.
- Verified implementation commit: `dc2a235d663e6dab2f15483a2c584ad419f3aebf`.
- [CI run 36214642161](https://github.com/Crusonia/Demeter/actions/runs/36214642161):
  passed on Python 3.11 and 3.12 at that implementation commit.
- Codex review requested on PR #29. The PR conversation is authoritative for its
  latest review status; a request is not an approval.

## Issue states

| Issue | Run status |
| --- | --- |
| #1 | Evidence extraction/applicability improved; scientific acceptance unmet |
| #6 | Not started; follows #1 |
| #7 | Not started |
| #23 | Not started |
| #8 | Not started |
| #24 | Not started |
| #25 | Not started |
| #9 | Not started |
| #26 | Not started |
| #27 | Open; no completion checkboxes changed |

## Implemented and preserved

The existing NumPy engine has 101 age groups, three living metabolic states,
explicit deaths/aging, zero births/migration, independent period life tables,
paired parameter uncertainty, and Sobol sensitivity. It remains validation-only.

This run adds source receipts and reproducible extraction for six clinical
benchmarks; machine-readable appraisals explain the population, endpoint, and
estimand mismatches. Benchmark records cannot drive engine inputs. The original
roadmap/backtesting specifications were recovered exactly from their existing
documentation branch. No downstream milestone module or public UI was added.

## Data and scientific limits

- Active demographic inputs: NCHS 2022–2024 life tables; Census Vintage 2025
  estimates for those years.
- New clinical benchmarks: corrected Rooney/ARIC 2021 paper (2011–2017 follow-up)
  and Koyama/LEADR 2022 paper (2010–2018 EHR observations).
- Verified hashes, interval extraction, correction metadata, source populations,
  and licenses are in the registry and `docs/validation/issue-1-clinical-sources.json`.
- No clinical benchmark was promoted to an active coefficient. National state
  shares, transitions, mortality ratios, dietary response, and lag remain synthetic.
- Model dependence on those values prevents substantive leverage findings.

Mortality reconstruction error is below 0.000020 year at every tested age/year/sex.
The existing 2022→2023 frozen-mortality forecast has a −0.964478-year life-expectancy
error and a 0.004469708 qx RMSE. This is a retrospective persistence benchmark;
there is **no independently validated dietary/health-state forecast** yet.

## Verification performed

| Check | Result |
| --- | --- |
| `uv sync --locked`, including a fresh separate environment | Pass |
| `uv run ruff check .` | Pass |
| `uv run pytest` | 70 passed; also passed in fresh environment |
| `uv run demeter validate` | Software pass; science not ready |
| `uv run demeter validate --scientific-required` | Expected exit 1 |
| `uv run demeter evidence audit` | Pass; unresolved science disclosed |
| `uv run demeter evidence applicability` | Pass; replacements remain unidentified |
| `uv run demeter evidence verify-sources` | Six point/CI estimates verified |
| Baseline and reduced-UPF CLI simulations | Pass, validation-only |
| Scenario comparison | Pass, validation-only |
| Paired uncertainty: 128 draws, seed 42 | Pass, synthetic parameter ranges |
| Sobol sensitivity: 64 base samples, seed 42 | Pass, synthetic parameter ranges |
| Historical backtest: train 2022, holdout 2023 | Pass as limited benchmark |
| `uv build`; install wheel and load baseline/evidence API | Pass |
| `git diff --check` | Pass |

## Required next action

Continue #1 on the same branch/PR. The exact remaining acceptance gates are in
`docs/ISSUE_1_AUDIT.md`: age/sex baseline state estimation, identified competing
transition hazards, mortality decomposition, evidenced food dose/endpoint/lag,
and an independent historical health holdout.

The inspected ARIC individual-level route requires a researcher request and
permitted-use agreement; no authorized access was supplied. That is an access
constraint for that route, not a conclusion that all alternative evidence is
unavailable. A qualified research owner can obtain permitted data, provide an
equivalent longitudinal package, or identify sufficiently detailed compatible
published transition tables for appraisal. No account was created or agreement
accepted on the user's behalf.

Do not merge/close #1 as completed, start unsupported dependent mechanisms, or
advance the #27 checklist merely because code review and software CI pass.
After scientific #1 acceptance, proceed to #6 using the recovered historical
strategy. The recommended next work remains completion of this milestone,
not provider economics, agriculture, or a public simulator.
