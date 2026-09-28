# ADR-22: Versioned local scenario and module packages

- Status: proposed
- Issue: [#22](https://github.com/Crusonia/Demeter/issues/22)
- Author/date: Codex at the maintainer's direction, 2026-09-28
- Implementation: this issue's PR; maintainer disposition is the merge record
- Scientific assessment: unchanged equations; clinical calibration deferred
- Supersedes: none

## Decision and scope

Extend API 1.0 with a declarative package manifest and explicit local registration.
The source-controlled catalog classifies approved project packages as canonical
or experimental. A separate ignored local registry links immutable version/hash
identities to third-party directories. Metadata includes authors, license,
software/API/structure compatibility, evidence and validation declarations.
External packages cannot claim project classification or use the reserved
`demeter.*` namespace. Catalog modifications require normal project review.

Inspect/list/register verify metadata and pinned files without importing code.
Run/compare explicitly select a scenario and optional single-file Python factory.
Use the existing immutable module inputs and engine-owned mortality/flows;
do not introduce another runtime, equation engine, parameter fitting or UI.
Optional evidence files can append namespaced parameters/source receipts and
blockers; they cannot replace existing records or datasets. Clone and validate
the base evidence before importing package code. Scientific execution is not
enabled by a publisher's metadata claim.

Every simulation identifies registered packages or explicit unregistered module
execution. Registered results retain full manifests and source/input hashes,
selection, separate base/merged evidence hashes and actual active evidence audit.
Author assertions of software testing are distinct from checks performed during
execution and never confer scientific approval.

The comparison command permits alternate existing health structures while
requiring common horizon, vintage, sex and population. Limit subtraction to
commensurate mortality/longevity outcomes, retain both full state contracts,
and label the result as a deterministic descriptive contrast. Different
allocations and assumptions can contribute; no causal attribution is implied.

## Alternatives and consequences

Python entry-point discovery/pip installation could silently import packages or
change a user's environment. A remote registry would add operational and trust
work unrelated to current model acceptance. Local explicit selection is enough
to compare community alternatives now; distribution/authentication can follow.

Hashes cover listed files and exact manifests. They are not signatures and do
not cover arbitrary transitive imports. Python runs with the user's permissions,
not in a security sandbox. Preserve the environment and core source commit.
The existing release tool captures tracked source and canonical outputs; it does
not yet package arbitrary external directories. This limitation is explicit.

Predeclared checks cover canonical parity, null parity, cross-structure metric
scope, import-free inspection, CLI roundtrips, immutable version pins, path and
source drift, reserved identities, incompatible contracts, additive evidence,
unchanged base evidence, unresolved/benchmark dependencies, and provenance.
CI runs these checks on all supported platforms. Existing evidence/source audits,
full tests, lint, distribution checks and canonical release replay remain gates.
No new clinical numeric values, equations or scientific RFC are introduced.

## Review and interests

AI-assisted authorship; no relevant conflicts known. Independent software or
scientific review is not claimed. Final validation and disposition belong in the PR.
