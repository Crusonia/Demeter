# Demeter v0.1 — Codex Cloud Objective

## Mission

Turn the existing validation scaffold into the first scientifically auditable Demeter model.

Demeter v0.1 must answer a deliberately narrow question:

> Given a U.S. population mortality schedule and explicit metabolic-health states, how do evidence-linked changes in selected dietary exposures propagate through metabolic-state transitions and mortality to period life expectancy and healthy life expectancy, with uncertainty shown rather than hidden?

The purpose of v0.1 is **not** to prove that a particular diet increases lifespan. The purpose is to establish a trustworthy computational architecture capable of evaluating such hypotheses without confusing assumptions with evidence.

Work autonomously until the acceptance criteria are met or a genuine evidence/data blocker is reached. Do not stop merely because the first implementation runs.

---

## Read first

Before changing code, read:

1. `AGENTS.md`
2. `README.md`
3. `evidence/parameters.yaml`
4. `src/demeter/schema.py`
5. `src/demeter/model.py`
6. all tests

Inspect current dependency APIs before relying on assumptions about them.

---

## Non-goals

Do not build these in v0.1:

- agriculture acreage or production models
- farmer or consumer agent-based models
- food-company models
- policy optimization
- healthcare-cost forecasts
- investment scoring
- Next.js / Vercel UI
- a database service
- LLM-generated causal parameters
- a broad disease model covering every chronic condition

Leave extension points where useful, but do not spend implementation time on future modules.

---

# 1. Population and mortality foundation

Replace the validation-only closed cohort with an age-structured U.S. population/life-table foundation.

Requirements:

- Represent explicit age cohorts sufficient to reproduce an authoritative U.S. period life table.
- Preserve sex stratification if the chosen authoritative source supports it cleanly; otherwise build the schema so it can be added without changing model semantics.
- Keep population, deaths, aging, and any births/migration flows explicit.
- Separate demographic mechanics from metabolic-state mechanics.
- Implement an independent life-table calculation with tests.
- Reproduce source life expectancy within a documented numerical tolerance before adding dietary effects.

Preferred authoritative sources:

- CDC / NCHS U.S. life tables
- U.S. Census population estimates where needed

Use the most recent authoritative data that can be downloaded reproducibly. Record source vintage and retrieval metadata.

Do not scrape an undocumented secondary table if a machine-readable government source exists.

---

# 2. Metabolic health states

At minimum represent:

1. metabolically healthy / normoglycemic
2. insulin resistant / prediabetes
3. type 2 diabetes

Transitions must be explicit and population-conserving.

Candidate transition families:

```text
healthy -> prediabetes
prediabetes -> healthy
prediabetes -> T2D
T2D -> improved/non-diabetic state only where definition and evidence justify it
state -> death
```

Do not encode "remission" casually. Define the modeled state and evidence precisely.

Use age-specific transition rates when evidence materially supports them. If data do not justify age-specific rates, use the simplest defensible structure and document the limitation.

Baseline prevalence and incidence should be checked against authoritative U.S. observations, favoring CDC/NHANES and peer-reviewed analyses of those data.

---

# 3. Dietary exposure layer

Keep v0.1 exposure scope small.

Start with no more than three candidate exposures unless evidence quality strongly favors fewer:

- ultra-processed-food share
- fiber intake
- fruit/vegetable intake

For each exposure:

- define units and baseline distribution
- define the modeled health endpoint it directly modifies
- record whether evidence is causal, observational, mechanistic, or assumption-based
- record study population and exposure range
- record effect uncertainty
- prohibit silent extrapolation outside the supported exposure range

Avoid double counting correlated exposures. If UPF and fiber effects overlap materially, either model that covariance or explicitly restrict the interpretation.

Do not turn nutrition scores into causal parameters without evidence.

---

# 4. Evidence registry

Evolve `evidence/parameters.yaml` into an auditable registry rather than bypassing it.

Every model parameter must include, as applicable:

```yaml
key:
value:
unit:
status: observed | estimated | derived | synthetic
evidence_grade: A | B | C | D | E
source:
source_url:
citation:
population:
geography:
time_period:
exposure_definition:
outcome_definition:
uncertainty:
transformation:
model_role:
notes:
```

Evidence grades:

- **A** — strong causal evidence / high-quality randomized or convergent causal evidence
- **B** — strong prospective or high-quality observational evidence with substantial adjustment
- **C** — observational/mechanistic evidence useful but causality uncertain
- **D** — expert/modeling assumption
- **E** — synthetic software-validation placeholder

The grade is metadata, not a mathematical truth. Document the rationale.

No fabricated citations. If evidence is unresolved, mark it unresolved and keep the model from presenting a substantive result that depends on it.

---

# 5. Provenance and data pipeline

Add a reproducible data ingestion layer.

Suggested layout:

```text
data/
  raw/            # immutable downloaded source artifacts; normally gitignored
  processed/      # model-ready generated artifacts; normally gitignored
  manifests/      # committed metadata, checksums, URLs, retrieval dates

src/demeter/data/
  fetch_*.py
  transform_*.py
```

For every external dataset:

- source URL
- publisher
- dataset title
- vintage/release date
- retrieval date
- checksum
- transformation script
- output schema

A fresh environment should be able to rebuild processed inputs from authoritative sources, subject to source availability.

Never commit restricted or personally identifiable health data.

---

# 6. Model engine

The repository currently includes BPTK-Py because Demeter is fundamentally a systems-dynamics project.

Evaluate BPTK-Py 3.x against the v0.1 requirements before committing to it for every equation.

Use it where it makes stocks, flows, delays, dimensions, scenarios, or model inspection clearer.

A transparent NumPy implementation is acceptable for life-table or cohort mechanics when it is easier to test and audit.

Do not bury core equations in framework magic.

The final architecture should make these separations obvious:

```text
evidence/data
      ↓
parameterization
      ↓
population + metabolic state equations
      ↓
scenario
      ↓
simulation
      ↓
life table / outcome calculation
      ↓
uncertainty + sensitivity
```

---

# 7. Uncertainty

A single deterministic output is insufficient.

Implement uncertainty propagation for material parameters.

At minimum:

- sample from recorded parameter uncertainty
- deterministic random seed support
- report median and uncertainty intervals
- separate parameter uncertainty from scenario uncertainty where practical

Do not imply that an uncertainty interval captures structural/model uncertainty unless it actually does.

Add SALib-based global sensitivity analysis after the core model is stable.

The CLI target is:

```bash
uv run demeter sensitivity life_expectancy
```

The result should identify which uncertain parameters dominate variance in the selected outcome.

---

# 8. Calibration and validation

Validation is a first-class product requirement.

At minimum implement:

### Baseline checks

- life expectancy vs authoritative U.S. life table
- age-specific mortality vs source mortality
- diabetes / prediabetes prevalence vs authoritative observations
- population conservation

### Historical backtest

Choose at least one historical start point for which source data allow a meaningful forward comparison.

Do not "backtest" against a target using parameters calibrated to the same target without saying so.

Report calibration targets separately from holdout validation targets.

### Behavioral tests

Where supported by model semantics:

- zero intervention reproduces baseline
- equivalent scenarios produce equivalent results
- invalid exposure ranges fail clearly
- population remains nonnegative
- transition rates remain bounded
- reduced progression hazard cannot mechanically increase progression in the same step
- life-table implementation matches known fixture calculations

---

# 9. CLI

The CLI is the v0.1 product surface.

Required:

```bash
uv run demeter validate

uv run demeter simulate scenarios/baseline.yaml

uv run demeter simulate scenarios/reduce_upf_30.yaml

uv run demeter compare \
  scenarios/baseline.yaml \
  scenarios/reduce_upf_30.yaml

uv run demeter sensitivity life_expectancy
```

Add:

```bash
uv run demeter evidence audit
```

or an equivalent command that reports:

- unresolved parameters
- synthetic parameters
- missing uncertainty
- missing provenance
- evidence-grade counts

Outputs should support both readable terminal summaries and machine-readable JSON.

---

# 10. Output semantics

Every result must include:

- model version
- scenario identifier
- source-data vintage
- parameter/evidence version or content hash
- whether synthetic/unresolved parameters affected the result
- uncertainty interval when applicable
- key limitations

Never print a headline such as "life expectancy increases X years" if unresolved/synthetic parameters materially determine X.

For development outputs, use an unmistakable marker such as:

```
VALIDATION ONLY — NOT A SCIENTIFIC ESTIMATE
```

---

# 11. Testing and CI

CI must run on every pull request.

Required checks:

- unit tests
- integration tests for CLI baseline run
- evidence-registry validation
- Ruff lint
- deterministic fixture comparison

Prefer fast tests. Mark expensive Monte Carlo or data-download tests separately.

No network dependency in the ordinary unit-test suite.

---

# 12. Documentation

Update README with:

- what Demeter is
- what v0.1 can and cannot claim
- architecture diagram
- setup
- CLI examples
- evidence model
- data provenance
- validation status
- known limitations
- roadmap to agriculture

Add a short technical model specification in `docs/MODEL_SPEC.md` describing equations and units in plain English and mathematical notation where useful.

---

# Definition of done

Do not call the work v0.1 complete until:

1. a fresh clone installs reproducibly
2. CI passes
3. baseline simulation runs from CLI
4. authoritative life-table baseline is reproduced within documented tolerance
5. metabolic states and transitions are explicit and population-conserving
6. scenario inputs are typed and bounded
7. all substantive parameters are evidence-linked
8. synthetic placeholders cannot silently contaminate substantive outputs
9. uncertainty propagation works
10. sensitivity analysis works
11. at least one historical validation/backtest exists
12. tests cover conservation, life-table arithmetic, evidence completeness and scenario behavior
13. model limitations are documented
14. no agriculture/UI scope has leaked into the implementation

When complete, produce a concise PR summary containing:

- architecture
- data sources and vintages
- validation results
- remaining uncertainty
- commands run and their status
- explicit unresolved scientific questions

The goal is not maximal code. The goal is a small model we can trust enough to extend.
