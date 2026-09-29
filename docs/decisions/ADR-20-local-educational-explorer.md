# ADR-20: Local educational Explorer with a separate Python engine

- Status: proposed
- Issue: [#20](https://github.com/Crusonia/Demeter/issues/20), a bounded local precursor;
  this implementation does not close the public simulator issue
- Decision and implementation PR: [#54](https://github.com/Crusonia/Demeter/pull/54)
- Author/date: Codex at the maintainer's direction, 2026-09-28
- Maintainer disposition: pending; no independent review or acceptance is claimed
- Implementation: local learning interface implemented in PR #54
- Scientific assessment: no model semantics changed; no scientific RFC required
  under the [review policy](../SCIENTIFIC_REVIEW.md); outputs remain validation-only
- Related design: [project vision](../PROJECT_VISION.md),
  [system architecture](../SYSTEM_ARCHITECTURE.md),
  [scenario catalog](../SCENARIO_CATALOG.md),
  [release provenance](ADR-21-reproducible-releases.md)
- Supersedes / superseded by: none

## Context and constraints

New readers need explanations beside charts and an approachable way to change an
assumption, predict its effect, run the existing model and reflect on the result.
The Python library and CLI remain the sole implementation of model equations.
The interface must preserve evidence status, units, uncertainty and the distinction
between software exercises and scientific findings. It must not activate future
agriculture, retail value capture, healthcare economics or public deployment.

The user requested Next.js and novice setup on Windows, macOS and Linux. Routine
use should need one launcher, without a separate Node service, account or database.
The existing offline HTML report must remain available. Completed results must
remain tied to their original assumptions even while a reader edits a new run.

## Alternatives and decision

1. Keep only the CLI and offline reports. This has the smallest dependency surface,
   but does not provide a guided prediction, rerun and comparison exercise.
2. Run a full Next.js server alongside a Python API. This supports a future hosted
   application, but adds a second service without helping the current local scope.
3. Port model equations to browser JavaScript. This removes the Python service but
   creates a second engine requiring independent scientific and numerical parity.
4. Serve a static Next.js export from an optional Python service. This is the
   implemented choice: React handles presentation and Python handles every run.

`demeter explore` starts one loopback FastAPI/Uvicorn service and opens the browser.
The `studio` extra contains the optional Python dependencies. Node 24 is needed
for source builds; installed wheels serve bundled static assets. The ordinary CLI
and Python library do not import or require the web stack. Browser assets and
Plotly are served locally. Host/origin checks and a per-launch session token scope
the local API; this is not a multi-user authentication or public hosting design.

The adapter exposes only the reviewed project catalog. Form edits are translated
into validated canonical scenarios and evidence snapshots. Observed, estimated
and derived evidence stays read-only; advanced edits apply only to active synthetic
parameters. Range endpoints pass the existing module validators. A change of
structure clears incompatible overrides. There are no new equations or evidence
values in this decision.

A single spawned worker executes a run at a time. Atomic receipts, a directory
lock and explicit failed/cancelled/interrupted states avoid ambiguous completion.
Each run freezes its request, settings, resolved scenario/evidence, teaching content,
source/data fingerprint and reference results. Later reflections are separate notes.
A compatible saved reference must share the base registry, source/data fingerprint,
population selection, horizon, vintage, mode and structure. Nominal comparisons
show absolute and relative changes plus an assumption diff; independent uncertainty
bands are never subtracted to manufacture a confidence interval for the difference.

Chart commentary is reviewed Markdown shared by the interface and offline reports.
Computed summaries describe actual results. Planned domain menus link to design
documents and cannot initiate unimplemented models. The interface does not bypass
the scientific release gate or represent v0.1 acceptance as complete.

## Consequences and verification

The local HTTP adapter, frontend and build tooling add maintenance work. The static
export cannot supply server actions; new interactions must use the explicit Python
API. The file-based store is suitable for one local writer, not a shared service.
Large uncertainty and sensitivity jobs still take the time required by the canonical
engine. Preview sample counts are teaching settings, not evidence of convergence.

No existing scenario, evidence or model API migration is required. The web API and
run files are alpha implementation details; retain complete run directories and the
matching source checkout. They do not replace release archives. Future persistence
changes must preserve old runs or provide an explicit migration. Rollback consists
of using the existing CLI/offline reports and retaining saved run directories.
Generated source-build assets live in ignored `build/explorer/`, outside the
scientific source tree; wheels include those assets and reviewed commentary.

Completed software checks for implementation commit `87340b5`:

- Windows: 399 Python tests, Ruff, TypeScript, three frontend data tests and the
  production static build passed.
- Desktop/mobile Chromium: a real run and rerun against a frozen reference,
  assumption differences, reopened notes, chart/data/source navigation and exports
  passed with no external asset requests or JavaScript errors.
- Wheel/sdist contents, installed-wheel serving and a fresh editable source install
  without compiled assets passed. Source/data redistribution checks remained active.
- [CI run 36439701271](https://github.com/Crusonia/Demeter/actions/runs/36439701271)
  passed on Windows, macOS and Linux with Python 3.11/3.12 coverage, including
  package auditing and numerical replay; the Linux 3.12 job ran the browser workflow.

These are software checks, not scientific validation or human approval. Current
commit checks and review dispositions belong in PR #54. Reconsider this architecture
before public hosting, multiple users, concurrent workers, remote evidence, new
model families or changes to comparison semantics. Those capabilities require
their own bounded design and review; issue #20 remains open for the public surface.

## Review and interests

This is AI-assisted software, presentation and documentation work without a change
to model semantics or an appraisal of clinical effects. Human authors, reviewers
and the maintainer must record their own relevant interests; this record does not
make personal disclosures on their behalf. Independent software review and the
maintainer's acceptance/rejection/deferment rationale remain pending in PR #54.
Scientific approval is not claimed, and model results remain validation-only.
