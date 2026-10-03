# NHIS verified-delivery guard

Status: proposed software trust boundary, with synthetic tests only. This step
does not inspect real participant fields, admit an empirical calculation, add a
registry parameter or invoke a clinical model. The reviewed contract is committed
before its implementation.

The existing [acquisition protocol](NHIS_NATIVE_SOURCE_ADMISSION.md) and
[delivery result](NHIS_NATIVE_FRAMING_RESULT.md) establish the original archive
and native identities. The separately reviewed
[record contract](design/11_NHIS_NATIVE_RECORD_CONTRACT.md) defines a finite
decoder language; it does not admit a real-source caller. This guard connects
those identities to the loaded implementation before any selected-value read.
Its design trace is I-01/I-07/I-11/I-12 -> F-08 -> T-01/T-02/T-05/T-08 under
[RFC-56](rfcs/RFC-56-observation-state-mapping.md), with the current
[health-slice objective](CODEX_V0_1_OBJECTIVE.md) unchanged.

## Fixed inputs and order

The guard accepts explicitly supplied local archive/native file paths and an
explicit repository root. It performs no network access, archive extraction to
disk, source-file repair or default search for participant files. Errors expose
only fixed messages, without paths, member names or selected values.

Before returning native bytes, it verifies in this order:

1. Exact pinned bytes of the original framing protocol, framing receipt, typed
   diagnosis metadata receipt and native record contract under the supplied
   root, using bounded reads before materializing documentary/code files as well
   as source files. JSON is read strictly, rejecting duplicate keys, nonfinite values and
   non-object receipts. The fixed receipt identities are independent of caller
   supplied metadata; changing a receipt and recomputing its internal hash cannot
   make it pass.
2. Expected decoder and diagnosis-classifier file identities, both on disk and
   at the origins of the actually loaded modules. Loaded implementations must
   belong to the supplied source checkout, with matching bytes. No decoder or
   classifier function is invoked during admission; importing a Python module
   executes its definitions. The guard is a small reviewed entry point; it is
   not a defense against deliberate in-memory function replacement.
3. Local archive and native files with bounded reads, exact size and SHA256
   identities. No parser receives bytes before both identities pass. A 100 MiB
   workflow cap is a resource policy, not an empirical threshold. Source files
   are never rewritten. File-read errors, unsupported formats and mismatches
   stop the call without returning partial content.
4. Exactly one ordinary unencrypted ZIP member named `adult25.dat`, with the
   frozen CRC, declared sizes and no unexpected archive comments. Reading that
   member validates CRC and its bytes must equal the separately pinned native
   bytes. No path extraction occurs.
5. Exact 685-byte printable-ASCII payloads followed by CRLF, final CRLF and the
   frozen physical record count. No trimming, padding, recoding, guessed checksum
   algorithm or field projection occurs.

The frozen delivery is archive SHA256
`1981733845c4d6ede66f4756c34d47b356fbe403820c0ed33825d21e4d8f21e4`,
2,837,893 bytes; native SHA256
`48b2d91002c9f30e03e87e33d37041dc991ea43a390674045a9ca60c7d004b95`,
16,635,705 bytes, 24,215 physical records, ZIP CRC `a1cc80ff`. These are delivery
observations in the original receipt, not scientific parameters or estimates.
The producer's published checksum algorithm remains unverified.

The implementation's expected decoder/classifier identities will be fixed from
their reviewed source commits before the guard is used. A future change needs
an additive admission decision, not modification of the original protocol or
receipt. The pure decoder, classifier and joint survey kernel remain unchanged.

## Return value and limits

Success returns an immutable private delivery object containing exact native
bytes and fixed technical provenance. Its representation omits source paths,
bytes and participant values. There is no automatic decoding, public export,
CLI, weight filtering, deduplication, ratio/covariance, confidence interval or
model initialization. Private handling is not an anonymity guarantee against
a caller deliberately exporting attributes.

The delivery object records `source_delivery_verified`, which describes these
byte and code checks only. It also records `source_admitted: false` and all five
scientific gates as false: `direct_initialization_allowed`,
`clinical_fit_allowed`, `engine_activation_allowed`,
`sampling_distribution_assumed` and `scientific_release_ready`. A synthetic
fixture whose pins are replaced by a test cannot establish real-source
admission. Source documentation and summaries were already seen: this is
used-source development, not preregistration or independent validation.

Before real selected-value inspection, a separately reviewed and committed
intake/code-admission receipt must bind the exact loaded guard and helper bytes,
source identities and a fixed private diagnostic schema. Before any empirical
survey estimate, the estimand, missing/universe handling, annual weights/full
design, degrees of freedom, interval/presentation policy and nonreconstructive
disclosure schema also need separate review. The guard cannot resolve those
statistical or clinical questions by passing delivery checks.

## Verification

Synthetic checks must independently cover a successful local byte delivery;
source/receipt/loaded-origin tampering before any decoder callback; oversized or
missing files; malformed JSON; archive member/encryption/comment/CRC mismatches;
byte-width, separator and non-ASCII refusal; sanitized errors; immutable private
results and closed gates. Preserve failed checks. Run the existing eight model
parity comparisons, the package inventory audit, focused tests, full pytest and
Ruff on the final implementation. These are software checks, not clinical proof.
