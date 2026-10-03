# NHIS 2025 selected-field inspection contract

Status: reviewed technical contract prepared for contract-first implementation.
The new library implementation, independent code/source admission and actual
selected-field inspection remain pending. This document authorizes no original
participant-field call, source request, empirical estimate or clinical use.
Its companion [fixed schema](validation/nhis2025-selected-field-inspection-contract-v1.json)
records the reviewed definitions. All five scientific gates remain false.

This follows merged PR107 at `b6ff0bf9cd84c45a9a8eb7621705f4e3f28710a8`,
whose tree equals reviewed `75cc2f4c0837cb0a6ba62708fc43c75babfcf631`. The
[delivery guard](NHIS_SOURCE_GUARD.md),
[native contract](design/11_NHIS_NATIVE_RECORD_CONTRACT.md),
[framing protocol](validation/nhis2025-native-framing-protocol-v1.json) and
[framing receipt](validation/nhis2025-native-framing-receipt-v1.json) are unchanged.
The [synthetic survey witness](design/10_NHIS_SURVEY_WITNESS.md) remains separate.

## Review chronology and accepted correction

Ignored v1 and v2 MD/JSON drafts and the independent v2 review are preserved by
exact hashes in the companion schema. Root selected library-only/in-memory scope,
all five private label-support scalars and no writer/CLI/public diagnostic counts.
The independent automated review found one pre-freeze clarification, accepted
before this contract: producer PDF 124 defines DIBTYPE_A's literal universe as
`HHSTAT_A=1 AND DIBEV_A=1`. With HHSTAT=1, documented DIBEV codes 2/7/8/9 are
known outside that source-code predicate even when the clinical answer is unknown.
Missing HHSTAT or diagnosis blank/reader-period stays unresolved under a separate
conservative missing-source-status policy, rather than literal string comparison.
The existing diagnosis classifier remains unchanged and retains its unknowns.
This is used-source technical design, not preregistration, empirical scientific
admission or independent human review. Original metadata/source receipts and
helpers are preserved. No original guard/decoder call occurred in this preparation.

Design trace: I-01/I-07/I-11/I-12 -> F-08 -> T-01/T-02/T-05/T-08, RFC-56,
the clinical observation contract and the current v0.1 health slice. The question
is whether this exact native delivery can be decoded without losing unknown,
inconsistent, missing-universe or unsupported-method records. It is not how many
Americans have current type 2 diabetes.

## Existing work and the smallest next boundary

Reuse the existing `verify_delivery`, `decode_native_records`,
`PrivateNativeBatch.private_ledger` and `classify_reported_diabetes` unchanged.
Their reviewed bytes already provide source identity/framing checks, finite
native decoding and a complete seven-category answer partition. The existing
`nhis_survey_witness.assess` remains a separate synthetic arithmetic witness;
this increment must not call it, bridge a source batch to its frame, convert
Decimal weights for estimation, choose domains, calculate covariance or infer df.
Existing generic cohort bounds have different outcome/death premises and do not
apply to a one-wave recorded-answer inspection.

The only proposed implementation is a library-only inspection orchestrator and
a fixed in-memory aggregate projection of the existing private batch. It needs no
new parser, classifier, likelihood, stochastic engine or scientific parameter.
There is no writer, CLI, public-count release or persistence. A future disk export
requires a separately explicit contract. The review chronology preserves the
original draft versions, documentary receipt and accepted source-role correction.

## Library interface

The proposed new entry point accepts explicit `archive: Path`, `native: Path`
and keyword-only `root: Path`, returning a repr-hidden private inspection result.
Its private diagnostics accessor returns fresh fixed aggregate dictionaries on
success and no partial diagnostics on failure. Its separate technical accessor
returns a fresh allowlisted envelope, including unavailable conservation on a
failure. It exposes no native bytes, private record objects or exception objects.
Function/class names may be chosen during implementation without changing this
finite input/output contract. No output path, writer, CLI or network input exists.
Implementation tests use only synthetic fixtures; original source calls require
the later independent code/source-admission and actual-inspection decision.

## Exact source and code identity

Preserve the acquisition protocol and source-framing receipt byte-for-byte.
Archive `adult25.zip`: SHA256
`1981733845c4d6ede66f4756c34d47b356fbe403820c0ed33825d21e4d8f21e4`,
2,837,893 bytes. Native `adult25.dat`: SHA256
`48b2d91002c9f30e03e87e33d37041dc991ea43a390674045a9ca60c7d004b95`,
16,635,705 bytes; 24,215 physical records, 685-byte printable-ASCII payloads plus
CRLF and a final CRLF. These are already disclosed delivery observations, not
new empirical outcomes. CRC `a1cc80ff` is separate from SHA256 source identity.

Bind these documentary artifacts independently: framing protocol `e1738706...`,
framing receipt `d669d228...`, typed metadata receipt `cbb7e50e...`, native decoder
contract `e2df9593...`. Full hashes appear in the JSON. Producer SAS layout
`2a774c19...`, survey description `d8a8cc99...` and PRICSSA `81437884...` were
verified against existing documentary originals. Source codebooks and frequency
tables were previously inspected, so this is used-source development, not blind
preregistration or independent scientific validation.

Current implementation pins are guard `dcb350b4...`, decoder `68042959...` and
classifier `0bf79f94...`. Before any real selected-field call, separately commit
the reviewed inspection contract, implement/test the thin orchestrator, and
freeze an independent source/code-admission receipt binding its actual bytes and
these invoked dependencies. The new orchestrator does not exist yet; its pin
cannot be invented now. Verify literal receipt identities, source/raw identities
and disk plus actually loaded module origins before invoking the helpers.
Do not use a mutable registry/code self-repin as independent admission.

The guard's normal verification function is the entry point. Direct construction
of a private Python object is not evidence of verified delivery, authorization
or anonymity. No guarantee is claimed against deliberate in-memory replacement
or attribute export. Provenance describes the reviewed call path.

## Proposed call order and failures

1. Before a future actual inspection, independently verify the immutable
   selected-field contract/admission and actually loaded code identities. No
   automatic participant-file search, network access, import of foreign
   implementations or source repair. This library-only increment has no output
   path, destination preflight or writer API.
2. Invoke `verify_delivery` with explicit archive/native/root paths. Preserve its
   independent documentary, loaded-origin, bounded source/ZIP/CRC and exact
   framing checks. The existing 100 MiB cap is a resource policy only.
3. After successful verification, call the unchanged private native decoder on
   the exact immutable bytes. No source normalization, padding, deduplication,
   implicit decimals or unsupported-code fallback.
4. Require decoded record count to equal the frozen delivery count and every
   declared private marginal to conserve all input records. Retain every record;
   this is record accounting, not proof of unique people or survey eligibility.
5. Return a repr-hidden private result object with fresh fixed aggregate
   dictionaries. Hold diagnostics in memory only; never return/persist private
   records, HHX keys, raw tokens, exact ages, weights or design codes. A separate
   fresh allowlisted technical envelope contains frozen provenance/reference
   count, stage/projection flags, conservation status and five false gates. No
   caller-supplied nested metadata or public count-table option is accepted.

Any admission, framing, lexical or role mismatch refuses the whole call. Do not
skip a malformed row or export a partial batch. Private error receipt fields are
fixed stage/status enums and integrity flags only: no values, paths, field
tokens, row indices, exceptions, traceback or free-text source failures.
Unexpected exceptions become a sanitized fixed structured failure, with no
chained private context. No partial diagnostic is returned. No file is created,
changed or deleted on any path; no persistence API exists.

The flag chronology must be honest. Before decoder invocation,
`selected_values_projected` is false. On complete decoding it is true. If a
decoder call fails after possibly processing earlier rows, it is **null/unknown**
and `selected_values_projection_status` is `possibly_partial`; never claim no
field was read merely because no batch returned. If decoding succeeded but
aggregate projection then fails, `selected_values_projected` remains **true**,
projection status remains `completed`, and conservation diagnostics are
unavailable rather than fabricated. All failure paths have no partial aggregate.
The result can expose a fixed sanitized failure dictionary; no original exception
object, dynamic message or traceback is attached. `empirical_estimate_computed`
is always false. `source_delivery_verified` describes byte/code verification,
not empirical scientific admission. `source_admitted` remains false in the
existing meaning used by these software witnesses; the new contract permits only
the explicitly scoped technical selected-field inspection after review.

## Fixed private aggregate diagnostics

The JSON names every key and category. No arbitrary source labels are allowed.
All unweighted marginal counts refer to the complete delivered record frame.
Unknowns remain in denominators; no positive-weight, known-type, age, sex, proxy,
Sample Adult flag or household-key filter is applied.

- The existing complete seven-category reported-answer partition, with unknown
  diagnosis, unknown diagnosed type and inconsistent type-universe preserved.
- Literal diagnosis/type response roles: documented codes plus separate native
  blank and reader single-period missingness. These are answer categories,
  never latent type or current disease.
- Sample Adult status (`sample_adult`, `missing`), age roles (exact, 85+, three
  documented unknowns, missing), sex and proxy known/unknown/missing roles.
  Proxy is not an exclusion or proof an answer was provided by the adult.
  No exact ages or age domains are published; 85+ is not age85 exactly.
- Type-question universe: known in-universe only when HHSTAT=1 and diagnosis=1;
  known outside when HHSTAT=1 and documented diagnosis code is 2/7/8/9. Unknown
  diagnosis codes 7/8/9 still remain clinical-answer unknowns in the unchanged
  classifier. Missing HHSTAT or diagnosis blank/period is unresolved under the
  conservative missing-source-status policy, not literal predicate evaluation.
  The six-cell
  **private** answer-presence/universe diagnostic conserves every record and
  does not revise the existing classifier. A missing HHSTAT plus a positive
  diagnosis does not become known Sample Adult universe.
- Weight signs (`positive`, `zero`, `negative`, `missing`) retain all records,
  without totals/means/quantiles or conversion from Decimal. Unsupported lexical
  syntax still refuses the entire call rather than becoming missing or zero.
- Stratum and PSU sign/missing partitions plus complete design-presence
  partition. Zero/negative codes are retained decoder-language values, not a
  claim that NHIS documents them as design groups. Include all five private
  label-support scalars: records with both design fields; distinct strata;
  distinct stratum/PSU pairs; strata with one recorded PSU label; and strata with
  multiple recorded PSU labels. All are restricted to records with both fields
  present, with no positive-code filtering. Empty support yields zero counts.
  They are label-support diagnostics, never df, eligibility or method selection.
  No code lists, per-stratum tables, variance or inferred design validity.
- Existing scalar key diagnostics: missing HHX, duplicate interpreted HHX records
  and number of interpreted keys having distinct lexical aliases. Do not export
  the keys or investigate linkage/identity. Do not deduplicate household records.
- Per-selected-field native blank and reader-period missing counts; they need
  not sum to the sample count because missingness across fields overlaps.
  Demographic/diagnosis/weight/design marginals are also overlapping facets;
  their counts are not summed into a larger population.

No cross-tab between diagnosis and age/sex/proxy/HHX/design, labelled record
paths, raw-token frequency table, estimated population total, rate, proportion,
mean weight, annual hazard, variance, sampling interval or fitted parameter is
included. Empty-source fixtures are useful for synthetic tests; the actual fixed
source hash/size/count cannot silently admit an empty delivery.

## Public envelope and the finite disclosure decision

The immediately proposed public envelope is technical only: fixed schema/stage,
original source and contract/code hashes, already disclosed reference record
count, verification/projection/inference flags, successful conservation booleans,
`diagnostic_counts_released: false`, attribution and all five false gates. It
contains no new observed marginal count, rare-code flag, exact design support,
weight/age summary, identifier, tuple or dynamic error text. Diagnostics stay
in memory and there is no private file export. A future persistence or public
count release must receive its own explicit contract before implementation.

The broad all-record count tables above are useful for determining whether
unknowns/universe exceptions and method eligibility need a later amendment.
They are private in-memory diagnostic dictionaries, not a public release.
This increment has no public diagnostic-count option or unresolved release
choice: the envelope is technical only. Later public marginals would be a
separate bounded design, without inventing an external-human approval gate. Do
not select cells or a
suppression threshold after seeing rare outcomes, use ad hoc top/bottom coding,
or claim NCHS reliability standards prove disclosure safety.

The [NCHS data-user agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html)
and survey-description PDF9 restrict use to statistical reporting/analysis,
forbid intentional identification, identifiable external linkage and research
on disclosure-protection methods. This inspection must not test reidentification.
The [agency materials policy](https://www.cdc.gov/other/agencymaterials.html)
requires attribution, no endorsement implication and clear free-source access;
third-party exceptions remain separate. Both public pages were ordinarily
retrieved as metadata on October 3; hashes are in the documentary receipt.

Producer PRICSSA PDF3 items2.4-2.10 describe annual weights, public WR design,
full-file subpopulation variance, interval/reliability and singleton conventions.
Those requirements concern a future estimate. This inspection produces no
percentages/intervals/df and chooses no NHIS estimator or reliability threshold.
Survey-description PDF17/121 provides proxy context; PDF35-36 warns about df;
PDF47-48/73-74 gives design/full-file context. None authorizes clinical type,
elapsed observation time, a person linkage or transport to all Americans.

## Synthetic falsification and unresolved choices

Test admission/refusal order with decoder spies, source/contract/code drift,
foreign loaded origins and coherent metadata self-repins. Test all recorded
answer/missing/universe combinations, demographic/topcode/proxy roles, retained
zero/negative/missing weights and design labels, duplicate/alias/missing keys,
full marginal conservation, row-order invariance and no input mutation. Use an
independent native-column fixture/oracle. Verify no invocation of survey witness,
model engine or network; no ID/token/row/traceback output; strict fresh schema
and repr-hidden results, without persistence or mutation of caller inputs.
Verify before-decoder failures have false/not_attempted; uncertain decoder
failures have null/possibly_partial; aggregation failures after successful
decoding have true/completed. No failure emits a partial aggregate.

Before any actual inspection, resolve only the new orchestrator actual bytes,
independent loaded-code/source admission and explicit authorization for the
selected-field run, after contract-first implementation and synthetic review.
The minimal library scope is now settled: all five private support counts, no
persistence, no CLI/writer and no public diagnostic counts. Survey target/domains,
weight exclusions, design conversion,
singleton method, intervals/df, NCHS reliability, public empirical release and
clinical transport remain later independent decisions, not intake defaults.

Software assessment: reviewed technical contract; new implementation/admission
pending, no original selected-field execution.
Scientific assessment: documentary technical design, no external expert or
empirical scientific acceptance. Maintainer disposition: exact contract freeze
pending root review; no actual selected-field inspection authorized.
Scientific use: no empirical findings or clinical use; all five gates false.
