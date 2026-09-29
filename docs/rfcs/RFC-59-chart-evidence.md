# RFC-59: Explain the evidence saved with each chart

- Status: proposed
- Issue and PR: [#59](https://github.com/Crusonia/Demeter/issues/59), [PR #62](https://github.com/Crusonia/Demeter/pull/62); supports #27
- Authors and date: Codex-assisted work for the Food is Health-affiliated project, September 29, 2026 (UTC)
- Implementation: implemented in [254b943](https://github.com/Crusonia/Demeter/commit/254b9438fb44d46c2a6974db9924718df8d59eca); verification below
- Scientific assessment: presentation/scope assessment below; external expert review pending
- Scientific use: validation-only; no model-parameter or clinical-claim change
- Supersedes / superseded by: none
- Maintainer disposition: pending; implementation does not imply RFC acceptance

The Sources tab currently shows the registry for almost every chart. A beginner
cannot distinguish a plotted historical observation from an active synthetic
coefficient or trace one graph arrow to its declared inputs.

Reuse the canonical diagnostics graph and its active parameter records. Attach a
chart evidence context to saved chart JSON and the offline HTML export. Snapshot
the relevant dataset definitions and baseline source receipts while observing the
run; rendering must never read today's registry to explain yesterday's result.
Historical charts use their own series source receipt. Trial benchmarks retain
their own eligibility, estimand, follow-up and uncertainty. Selecting an arrow
shows its directly declared parameters, not a claim of full causal identification.
Parameter-free arrows and missing replacement-module dependencies stay explicit.
Display the saved scenario separately from evidence, including exposure and access
schedules, coverage, prices and supply. Model contexts retain the saved component
limitations for diet response and GLP-1; independent benchmark views retain their
own study limits instead. Missing scenario context in older records is explicit.

The browser renders serialized Python results without implementing equations.
Reference charts retain separate evidence. Older saved runs that lack a context
show that absence; they are not silently reinterpreted with current evidence.
Reviewed teaching notes add prediction, assumption-challenge and evidence-needed
prompts. Existing saved notes remain supported without adding new prose to them.

No numeric inputs, evidence grades, engine equations or clinical claims change.
This is a local learning interface within the existing Explorer boundary, with
no production deployment. The alternative of showing the full registry remains
available in the global Sources view, but does not explain chart relevance.

Verify exact selection, snapshot independence, reference differences, historical
and trial scope, missing metadata, escaping, and unchanged numerical results.
Run Python/frontend checks and exercise desktop/mobile charts, reruns and offline
exports in a real browser. External scientific review and maintainer disposition
remain distinct from software verification.

Verification: all 440 Python tests, Ruff, frontend type checks, three JavaScript tests
and the static Next.js build pass. Real Chromium checks cover three model runs,
mechanism and historical evidence, saved scenario choices, GLP-1 assumptions and
limits, distinct references, notes, desktop/mobile and offline exports with external
requests blocked. One existing Starlette/httpx
deprecation warning remains. No independent human scientific review is implied.
