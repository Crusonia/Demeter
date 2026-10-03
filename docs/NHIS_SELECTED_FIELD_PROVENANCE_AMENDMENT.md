# NHIS selected-field inspection provenance amendment v2

Status: reviewed scope proposed for amendment-first freeze before implementation
commit. This is an additive technical-schema correction; the original
[contract](NHIS_SELECTED_FIELD_INSPECTION_CONTRACT.md) and its
[v1 JSON](validation/nhis2025-selected-field-inspection-contract-v1.json) remain
byte-identical. All classification, universe, missingness, conservation, privacy,
in-memory scope and five false scientific gates are unchanged.

## Finding and chronology

The v1 fixed private-success schema listed six SHA-only provenance keys, including
`code_admission_sha256`, although no actual-source execution receipt exists yet.
Independent automated review identified the contradiction before a successful
implementation/provenance output was frozen. An initial synthetic test rehearsal
used a five-key projection while this finding was under review; no original-source
guard, participant-field call or empirical output occurred. The rehearsal and
failed fixture checks remain ignored historical records. A missing receipt must
not be represented by an invented or null hash, or silently treated as optional.

Root selected a complete callable library orchestrator and an external reviewed
actual-run admission prerequisite. A hard-coded pending implementation boundary
patched away by success tests would not establish the callable library contract.
Normal flow verifies immutable contract/documents and existing helper disk and
loaded-origin identities before the existing guard, private decoder and aggregate
projection. Synthetic tests patch only delivery verification with declared
synthetic bytes, not this implementation flow. This amendment must be committed
before the implementation commit. It authorizes no actual-source invocation.

## Exact current technical provenance schema

Both current private success and public technical envelopes use exactly five keys:

- `archive_sha256`: original frozen archive identity.
- `native_sha256`: original frozen native identity.
- `framing_protocol_sha256`: unchanged original framing protocol identity.
- `framing_receipt_sha256`: unchanged original framing receipt identity.
- `selected_field_contract_sha256`: this amendment JSON identity, whose parent
  pins bind the original full inspection contract and Markdown.

Each value is a lowercase 64-character SHA256 string. Unknown keys are forbidden.
The immutable amendment and its Markdown, original contract and invoked helpers
are verified before source verification or decoding. No code-admission hash is
claimed by current synthetic/library technical outputs. A failed call has the
same fixed technical provenance and unavailable conservation; its separate
sanitized failure remains exactly the original v1 failure schema.

`code_admission_sha256` is reserved for a separately reviewed future original-source
execution/admission schema, backed by an independently committed receipt binding
actual reviewed implementation/helper bytes, loaded origins, exact sources and
this contract. The sixth key is not optional in the current schema: it is absent
by definition. A future receipt or schema cannot be invented by mutable registry
self-repin or caller-supplied metadata. Before any actual selected-field run,
that receipt and explicit reviewed execution decision remain prerequisites.
This increment neither creates them nor claims `source_admitted=True`.

The callable library's `source_delivery_verified` describes the existing byte
verification path, `selected_values_projected` preserves the honest decoder-stage
chronology, and `empirical_estimate_computed=False` describes the absence of any
estimator. None substitutes for the external actual-run admission. Integrity
claims cover the approved function path, not deliberate in-memory replacement.
No writer, CLI, persistence, public diagnostic counts or survey estimates exist.

Software assessment: additive schema correction before implementation freeze;
synthetic validation only. Scientific assessment: no empirical or external human
acceptance. Maintainer disposition: root-selected additive correction pending
exact amendment review/commit. Scientific use: none; all five gates remain false.
