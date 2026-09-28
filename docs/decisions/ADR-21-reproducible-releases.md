# ADR-21: Inspectable release bundles and explicit replay

- Status: proposed
- Issue: [#21](https://github.com/Crusonia/Demeter/issues/21)
- Author/date: Codex at the maintainer's direction, 2026-09-28
- Implementation: in this issue's PR; maintainer disposition is the merge record
- Scientific assessment: not applicable to unchanged equations; clinical fitting remains deferred
- Supersedes: none

## Context and decision

Individual outputs already identify evidence and source vintages, but cannot
alone recreate the source checkout, environment or release interpretation. A
version string alone is insufficient while an alpha changes between commits.

Add an offline release command producing an immutable destination directory:
source ZIP, complete canonical results, provenance manifest, checksum receipt and
model card. The source ZIP contains only Git-tracked files after the existing
rights/package audit; no raw caches, credentials from the environment, installed
dependencies or generated local outputs are copied. Reject symlinks. Record each
source path/hash, the Git commit and dirty state. A clean checkout is required by
default; an explicitly allowed dirty snapshot is marked development-only.

Separate software version, structure version, scenario/API compatibility, exact
evidence hash and exact source/data hashes. Version policy and a release checklist
describe when each changes. Keep clinical fitting, source-mortality reconciliation
and historical benchmark training/holdouts distinct. Archive failures and gaps.

Verification checks bytes and inventory without executing archived code. Replay
is an explicit command run with the archived source/environment: it requires
matching source/input bytes, recomputes the canonical calculations, and compares
numeric results with documented floating-point tolerances. Historical Git-location
metadata may differ after extraction; scientific inputs/outputs may not be ignored.

## Alternatives and consequences

Keeping only commands or a Git SHA relies on future data/network availability.
Bundling a virtual environment would be large, platform-specific and insufficient
for authenticity. Use locked dependencies plus the actual runtime inventory;
installation may require a network or a separately prepared package cache.

CI exercises bundle creation and replay and archives the resulting canonical
outputs. An engineering checkpoint in Git records a baseline and receipt against
a prior exact source commit, avoiding self-referential commit hashes. Permanent
published releases must retain the whole bundle; CI retention is not permanence.
No final scientific release or public registry publication is authorized by this
tooling change. Checksums detect changes; they are not signatures or scientific
approval. Only run code from a source you trust.

Predeclared tests cover modified/missing/extra artifacts, unsafe paths/symlinks,
dirty-state labeling, exact source inventory, deterministic run settings, altered
results and independent replay from an extracted source snapshot. Existing tests
and source/package audits remain required. No model equations or numeric evidence
change. Reconsider this format when remote/private inputs, extensions, or another
runtime require an explicit compatibility migration.

## Review and interests

AI-assisted authorship; no relevant conflicts known. Independent software or
scientific review is not claimed. Final checks and disposition belong in the PR.
