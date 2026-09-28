## What changes and why

Describe the problem and resulting behavior. Link an issue if there is one.

Change type: documentation / software / evidence / model semantics / architecture.
Link the scientific RFC and/or architecture decision, or explain why neither is
needed under [the review policy](https://github.com/Crusonia/Demeter/blob/main/docs/SCIENTIFIC_REVIEW.md).

## Evidence and interpretation

For model/data changes: sources, population, units, uncertainty, and any changed
assumptions or outputs. For other changes, write "No model semantics changed."
Identify the current phase or explain why this is a future proposal.

For evidence changes, link the before/after record: parameter keys, values, units,
status, evidence grade, distribution and bounds; exact source/version and archive
receipt; transformations; active versus benchmark role; and impact on outputs.
Explain grade/distribution changes and competing evidence. For causal changes,
state the estimand, alternatives, applicability, and predeclared validation plan.

## Validation

Commands run and results (including your operating system). Explain any checks
you could not run. A passing test suite is not scientific validation.

## Conflicts and review record

Authors: disclose relevant interests or state "No relevant conflicts known."
For documentation/software changes without scientific impact, explain that scope.
Each reviewer and the maintainer records their own relevant conflicts when reviewing.

For material scientific changes, keep these fields separate and update with actual
review links; leave absent reviews pending. Other PRs may mark scientific review/use
not applicable with a reason.

- Software assessment: pending (reviewer, reviewed commit, checks, limitations).
- Scientific review: pending (reviewer, expertise, independence, scope, disposition).
- Maintainer merge disposition: pending (decision and rationale).
- Scientific use: validation-only unless scoped acceptance is supported by linked evidence.

- [ ] The change is bounded and documented.
- [ ] Any new data have provenance, redistribution terms, and checksums.
- [ ] Synthetic/unresolved inputs remain visible and validation-only.
- [ ] Material scientific changes follow the RFC/evidence review rules; pending review is explicit.
- [ ] I have reviewed the diff for unrelated files, credentials, and private data.

Carter Williams (@jcarterwil) reviews and merges community contributions.
