# AGENTS.md — Demeter

## Mission

Demeter is a computational systems model of food, health, agriculture, longevity, economics, and policy.

The codebase exists to make causal claims explicit, testable, evidence-linked, uncertainty-aware, and reproducible. It is not a narrative model and it must never manufacture precision.

## Program context

Before making architectural decisions, read `docs/PROJECT_VISION.md`, `docs/SYSTEM_ARCHITECTURE.md`, and `docs/SCENARIO_CATALOG.md`. `PROJECT_VISION.md` is the canonical program rationale and phased roadmap; `SYSTEM_ARCHITECTURE.md` defines the mature module/runtime architecture and naming; `SCENARIO_CATALOG.md` preserves the intended future scenario surface. For work after v0.1, also read `docs/POST_V0_1_ROADMAP.md`; for calibration or validation work, `docs/BACKTESTING_STRATEGY.md` is authoritative.

Phase-specific objective documents may intentionally narrow scope. Do not interpret a narrow current phase as a change to the long-term program architecture unless the project vision is explicitly updated.

## v0.1 boundary

Build and validate one complete health vertical slice:

dietary exposure → metabolic state → chronic-disease risk → mortality → life expectancy / healthy life expectancy.

Do **not** add agriculture, food-company agents, farmer agents, policy optimization, a production web UI, or investment conclusions until the v0.1 acceptance criteria are met.

## Scientific integrity rules

1. Every substantive numeric parameter must be represented in `evidence/parameters.yaml`.
2. Every parameter must have a status: `synthetic`, `estimated`, `observed`, or `derived`.
3. `synthetic` parameters are allowed for software validation only. Outputs depending on them must be labeled validation-only and may not be described as findings.
4. Never invent a citation, DOI, dataset value, confidence interval, or causal effect.
5. Distinguish causal evidence from association. Record evidence strength separately from effect size.
6. Record population, geography, time period, units, transformations, and uncertainty for sourced parameters.
7. Prefer authoritative primary sources and peer-reviewed systematic reviews/meta-analyses. For U.S. baseline data, prefer CDC/NCHS, NHANES, USDA, Census and CMS as appropriate.
8. Keep raw evidence immutable. Derived data and model-ready data belong in separate locations with reproducible transforms.
9. Model uncertainty explicitly. Point estimates without uncertainty should be treated as incomplete unless the quantity is definitionally fixed.
10. Do not tune parameters merely to make a desired Food is Health conclusion appear.

## Modeling rules

- Preserve stocks and flows; population cannot disappear except through explicit mortality or migration flows.
- Define units for stocks, flows, rates and time.
- Add dimensional checks where practical.
- Keep model equations separate from scenario assumptions.
- Keep scenario assumptions separate from evidence.
- Use deterministic seeds for stochastic work.
- Prefer simple, inspectable equations over opaque complexity.
- Add complexity only when it improves an identified validation failure or represents a material causal mechanism.
- Track lags explicitly when evidence indicates delayed effects.
- Report absolute effects as well as relative effects.
- Never extrapolate an effect outside the studied population or exposure range without marking the extrapolation.

## Architecture

```
src/demeter/
  health/          # health-state and mortality model
  population/      # cohorts, life tables, demographic mechanics
  nutrition/       # dietary exposure representation
  evidence/        # typed access to parameter/evidence registry
  scenarios/       # scenario loading and validation
  analysis/        # sensitivity, uncertainty, attribution
  cli/             # command-line interface
```

The v0.1 model should be callable as a Python library and from the CLI. Do not couple the model engine to Vercel, Next.js, notebooks, or any database.

## Preferred technical stack

- Python 3.11+
- uv for environment/package management
- BPTK-Py 3.x for system-dynamics primitives where it improves clarity
- NumPy / Polars for numerical and tabular work
- PyYAML or typed equivalent for scenario/evidence files
- pytest for tests
- Ruff for lint/format
- SALib later for global sensitivity analysis
- PyMC later for Bayesian calibration
- Mesa later for agent-based modules

Do not force a framework where a transparent implementation is easier to verify.

## Required commands

The repository should converge on:

```bash
uv run demeter validate
uv run demeter simulate scenarios/baseline.yaml
uv run demeter simulate scenarios/reduce_upf_30.yaml
uv run demeter compare scenarios/baseline.yaml scenarios/reduce_upf_30.yaml
uv run demeter sensitivity life_expectancy
uv run pytest
uv run ruff check .
```

## v0.1 acceptance criteria

A v0.1 release is not complete until all of the following are true:

- U.S. population is represented in explicit age cohorts; sex stratification should be supported if source data justify it.
- At minimum, metabolic states include metabolically healthy, insulin resistant/prediabetes, and type 2 diabetes.
- State transitions conserve population.
- Mortality is age-specific and state-sensitive.
- Period life expectancy can be calculated from the model's mortality schedule.
- At least one health-adjusted longevity metric is defined or a documented path exists to add it without changing core model semantics.
- Dietary exposure scenarios affect model transitions only through evidence-linked parameters.
- Every nontrivial numeric parameter is traceable to the evidence registry.
- Baseline mortality is calibrated against an authoritative U.S. life table.
- Baseline diabetes/pre-diabetes prevalence is checked against authoritative U.S. observations.
- At least one historical backtest is implemented.
- Uncertainty can be propagated through scenario outputs.
- Tests cover conservation, bounds, monotonicity where justified, life-table arithmetic, scenario parsing, and evidence completeness.
- Baseline and intervention outputs clearly separate sourced values, derived values, assumptions, and uncertainty.
- README documents known limitations and unsupported interpretations.

## Working method for autonomous Codex runs

1. Read this file, `docs/PROJECT_VISION.md`, `docs/SYSTEM_ARCHITECTURE.md`, `docs/SCENARIO_CATALOG.md`, and any active roadmap/backtesting specification relevant to the task, then README, the active phase objective, evidence schema, and existing tests.
2. Inspect the repository before changing architecture.
3. Make the smallest coherent change that advances an acceptance criterion.
4. Run targeted tests after each meaningful change.
5. Run the full test/lint suite before finishing.
6. Update evidence metadata and documentation whenever model semantics change.
7. Leave the branch in a deployable/reproducible state; no broken placeholders or commented-out failures.
8. If a required external value cannot be verified, leave the parameter explicitly unresolved rather than guessing.
