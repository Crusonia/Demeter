# Reproducible releases and model cards

Demeter releases must identify the exact software, structure, evidence, data,
scenarios, environment and validation used. A package version alone is not a
scientific identity. The current software is an **engineering alpha**, with
clinical fitting deferred and scientific acceptance gates still open.

## Version policy

| Identity | Where recorded | Change policy |
| --- | --- | --- |
| Software/package version | `pyproject.toml`, `demeter.__version__` | Keep equal. Use `major.minor.patch` with Python prerelease suffixes such as `a1`. Fixes increment patch; compatible capabilities increment minor; incompatible public interfaces increment major. During 0.x, incompatible changes require a new minor and explicit migration notes. Advance the prerelease number for distinct published alpha builds. |
| Exact source | Git commit, dirty flag, every source path/hash, source-tree hash | Every bundle records exact bytes, even between package-version bumps. A dirty snapshot is development-only, never presented as a tagged release. |
| Model structure | `releases/profile.yaml:model_structure_version` | `annual-health-1` identifies the existing annual engine, state alternatives, operator order, lag mechanics and outcome definitions. Increment this identity when equations, states, timing or outcome meaning change, even if APIs remain compatible. Do not infer scientific acceptance from a structure version. |
| Evidence | Original YAML byte hash and normalized registry content hash | Any value, distribution, source, mapping, bound, status or grade change produces a new content identity. Preserve old registry bytes; explain the change through the evidence-review process. Never replace a benchmark with an active coefficient silently. |
| Source and model-ready data | Store/bundle manifests, source URLs/vintages/hashes and package audit | New vintages or transforms create new artifacts and hashes; preserve historical bytes. A later retrieval is not a later observation year. |
| Scenario schema and module API | Profile schema version, generated JSON schema, API version | Increment on incompatible parsing or exchange changes; provide migration examples. Successfully parsing an older file does not guarantee unchanged scientific meaning. |
| Release-bundle schema | `manifest.json:schema_version` | Increment for incompatible manifest/replay formats; retain a verifier for historical versions or document conversion. |

An evidence-only change can change outputs without changing structure. An
arithmetic bug fix may change outputs while keeping intended semantics; document
before/after results and increment the software patch/prerelease. Any changed
meaning also increments structure. Record breaking changes and migrations in the
profile before packaging. No published tag/artifact may be overwritten.

The profile's first structure identity describes existing code; it does not
retroactively certify earlier commits. The decision and alternatives are in
[ADR-21](decisions/ADR-21-reproducible-releases.md).

## Build an inspectable bundle

From a clean checkout with the locked environment:

```text
uv sync --locked
uv run demeter release build outputs/releases/my-checkpoint --draws 128 --samples 64 --seed 42
uv run demeter release verify outputs/releases/my-checkpoint
```

The destination must not exist. Local generated bundles belong under `outputs/`
and are ignored by Git. `--allow-dirty` is an explicit development option: stage
new reproducibility inputs first, and the bundle records both the base commit
and actual source hashes. Untracked model/evidence/scenario/release inputs are
rejected; unrelated untracked files are not copied. No installation, download,
calibration fitting, tag or GitHub release is performed by this command.

The resulting directory contains:

| Artifact | Meaning |
| --- | --- |
| `manifest.json` and `manifest.sha256` | Machine-readable identity, environment, configuration, schema, source/artifact inventory, evidence gaps, calibration status and validation references. |
| `source.zip` | Exact tracked code, tests, docs, scenarios, registry, locked dependencies, redistributable source datasets, derived bundles and notices. This is source, not an installed environment. |
| `results/baseline.json`, `intervention.json`, `comparison.json` | Complete canonical runs and absolute/relative scenario differences. |
| `results/uncertainty.json`, `sensitivity.json` | Seeded paired Monte Carlo and Sobol results, sample counts, assumptions and parameter dependencies. Sample counts alone do not establish convergence. |
| `results/validation.json` | Software/data arithmetic, prevalence discrepancies, source-life-table checks and explicit scientific readiness. |
| `results/historical.json` | Every benchmark series/fold, training years, interval-validation observations, holdouts, skipped folds, residuals and coverage. |
| `data-audit.json` | Source rights, vintages, hashes, manifests, transforms and offline reload recipes. |
| `MODEL_CARD.md`, `REPRODUCE.md` | Intended use, limitations, known gaps, compatibility, checks and reproduction instructions. |

The baseline/intervention paths are declared in `releases/profile.yaml`. This
format runs that canonical pair; optional experimental scenarios remain source
inputs, not separately validated or replayed claims. A scientific release needs
the acceptance evidence for every claimed scope and a reviewed profile migration.

## Verify and replay

Verification checks each artifact, exact ZIP membership, safe portable paths,
source hashes and manifest consistency. It does not run archived code or prove
authenticity. Keep the published manifest digest through a trusted channel;
someone who replaces both files and hashes can forge an unsigned bundle.

```text
uv run demeter release extract outputs/releases/my-checkpoint --destination outputs/replay-source
```

Extraction verifies first and requires a new destination. Review/trust the source
before executing it. In that extracted directory, run `uv sync --locked`, then
use an **absolute** path to the original bundle:

```text
uv run demeter release replay ABSOLUTE_BUNDLE_PATH --output ABSOLUTE_REPLAY_REPORT_PATH
```

Replay checks that the loaded source, evidence and data match the captured bytes,
recomputes all seven results and reports exact or tolerance-based equality.
Floating-point tolerance is relative `1e-10`, absolute `1e-8`, applied only to
floating values; integers, keys, labels, list lengths and other values must match.
Runtime inventories are reported so environment differences remain visible.
Only the historical report's Git commit/dirty-location metadata may differ after
extraction. No clinical value, data hash or other scientific metadata is ignored.
The original bundle is immutable; the replay report must be outside it.

Dependencies and Python binaries are not bundled. First installation may require
a network or a prepared package cache. Numerical replay is distinct from a raw
source rebuild: run the archived package reload recipes separately to validate
transformations. Fetch-only clinical article pages are intentionally excluded;
their pinned receipts and factual candidate parameters remain inspectable.

## Calibration and validation interpretation

The manifest explicitly separates three operations:

1. Clinical parameter fitting: **deferred**; no fitted parameters or fitting windows.
2. Existing mortality mixture reconciliation: matches the scenario's source-year
   schedule by age. This is a baseline normalization, not independent validation.
3. Historical observational benchmarks: training/interval-validation/holdout roles
   are recorded per fold. They neither calibrate clinical hazards nor validate a
   dietary effect. Retain unsuccessful predictions and coverage failures.

The model card exposes active synthetic parameters, registry-wide unresolved
records, missing uncertainty, unsupported interpretations and evidence gaps.
The alpha builder refuses to label a bundle scientifically accepted. A successful
byte check, numerical replay or test suite does not close #1 or #27.

## Release checklist

- Identify scope, intended users, geography, populations, unsupported uses and
  whether the artifact is a development snapshot, engineering checkpoint or
  scientifically accepted release. Current tooling supports the first two only.
- Review version changes, profile/schema compatibility, breaking changes and
  migration notes. Match package versions and record the exact clean source commit.
- Review source receipts, reuse terms, raw immutability, transformations, evidence
  statuses, distributions, transport decisions and unresolved records.
- State fitting windows and parameters, observation mappings and independent
  holdouts **before fitting**. Explicit absence is required when deferred.
- Run full tests/lint, source-store/rebuild/package audits, baseline/scenario runs,
  sensitivity/uncertainty diagnostics and relevant historical checks. Keep failures,
  coverage and convergence limits in the model card; retain CI links separately.
- Build a new bundle; verify it; extract it; install the archived lock; replay all
  results. Preserve the comparison report and actual environment inventory.
- Review the generated model card and archive complete canonical baseline outputs.
  Record actual software/scientific reviewer roles, expertise, conflicts and
  decisions; absence of independent review must remain explicit.
- For a scientific release, supply acceptance evidence and relevant independent
  assessment before changing scientific gates. An engineering merge is insufficient.
- With publication authorization, attach the **whole** bundle and checksum to an
  immutable versioned release/archive. Never substitute a mutable branch URL or
  an expiring CI artifact for permanent preservation. No final `0.1.0` tag while
  scientific acceptance remains incomplete.

CI builds/replays a small diagnostic bundle on each supported platform and retains
the Linux 3.12 bundle as a workflow artifact. That is an engineering receipt with
limited retention, not a scientific release. The [checkpoint archive](../releases/README.md)
keeps a canonical baseline and exact-source receipt in Git without duplicating
the full source ZIP.
