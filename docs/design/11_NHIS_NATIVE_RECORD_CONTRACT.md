# NHIS native record contract and synthetic decoder

Status: used-source field-contract proposal and synthetic software witness. No
participant fields are inspected by this increment. The
[native delivery result](../NHIS_NATIVE_FRAMING_RESULT.md) established bytes and
framing only; it did not admit a parser. This step defines how a future reader
could retain every answer, including missing and contradictory responses, before
any survey estimate is attempted.

This reviewed contract is committed before synthetic decoder implementation.
It does not freeze an empirical intake protocol or admit real source fields.

The design trace is I-01/I-07/I-11/I-12 -> F-08 -> T-01/T-02/T-05/T-08 in the
[input](04_MODEL_INPUTS.md) and [formulation](05_FORMULATION_AND_TESTS.md) records,
alongside [RFC-56](../rfcs/RFC-56-observation-state-mapping.md) and the
[reported-diagnosis design](09_NHIS_REPORTED_DIAGNOSES.md). The current
[v0.1 boundary](../CODEX_V0_1_OBJECTIVE.md) is unchanged.

## Source identity and documentary definitions

The inspected native source identity is SHA256
`48b2d91002c9f30e03e87e33d37041dc991ea43a390674045a9ca60c7d004b95`.
Its separately frozen [receipt](../validation/nhis2025-native-framing-receipt-v1.json)
records 685-byte payloads followed by CRLF and a final newline. No original bytes
are copied, altered or admitted by this contract. A future real-source loader
must independently verify the original ZIP/native identities and their receipt
before invoking the decoder.

The official [SAS layout](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Program_Code/NHIS/2025/Adult.sas)
has SHA256 `2a774c19872d66e0847c97ebb3804aca363df46f25d9fa5c3d4031908674507b`.
Its INPUT statement at lines 1633 onward uses these inclusive column ranges,
not a `w.d` informat or an implied-decimal suffix. The official
[codebook](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2025/adult-codebook.pdf),
version July 29, 2026, has SHA256
`e112f79ff5575e2900068471529bf884d43423c465c5275c4abf3becc4a818c5`.
Both are documentary originals identified by the earlier
[metadata receipt](../validation/nhis2025-typed-diagnosis-design-receipts-v1.json),
not newly acquired participant evidence.

| Selected field | Inclusive columns | Codebook PDF page | Role |
| --- | --- | --- | --- |
| `RECTYPE` | 1–2 | 1 | Declared Sample Adult record type 10 |
| `SRVY_YR` | 3–6 | 2 | Declared 2025 delivery vintage |
| `HHX` | 7–13 | 3 | Character household key; no prefix or person identity inferred |
| `WTFA_A` | 14–23 | 4 | Final annual adult weight; not an eligibility filter here |
| `PSTRAT` | 26–28 | 7 | Annual public variance stratum |
| `PPSU` | 29–34 | 8 | Annual public variance PSU |
| `PROXYFLAG_A` | 36 | 12 | Proxy used/not used and distinct unknown responses |
| `HHSTAT_A` | 38 | 14 | Sample Adult flag; only code 1 is documented |
| `SEX_A` | 46 | 19 | Male/female and distinct unknown responses |
| `AGEP_A` | 48–49 | 21 | Exact adult age, 85+ topcode, distinct unknown responses |
| `DIBEV_A` | 176 | 115 | Ever reported diagnosis; excludes gestational diabetes/prediabetes |
| `DIBTYPE_A` | 187 | 124 | Reported type; universe includes Sample Adult flag and diagnosis Yes |

The age definition explicitly lists 18–84, 85 for 85+, and 97/98/99 for refused,
not ascertained and don't know. These are coding definitions, not frequency-based
validity bounds. Sex and proxy fields explicitly list 1/2/7/8/9. Diagnosis lists
1/2/7/8/9 and type lists 1/2/3/7/8/9. Blank or missing Sample Adult status remains
unavailable, not an invented No; other unlisted flags are refused. A positive
diagnosis/type response does not resolve missing Sample Adult status.
Record type must be the declared Sample Adult type and year must be the declared
delivery vintage. Contradictory or missing record-type/year roles cause a
sanitized refusal; another record is never silently recast as an adult record.

## Declared decoder policy

This is a finite accepted-language adapter, not a complete SAS interpreter. It
accepts immutable bytes containing zero or more exact 685-byte payloads plus CRLF
and refuses short, long, mixed-separator or unterminated records without repair.
Payload bytes must be printable ASCII; unexpected control bytes are a software
refusal. The workflow resource cap is 100 MiB, inherited from the byte-acquisition
protocol and unrelated to an empirical or clinical cutoff.

Only the selected columns are retained privately. Native tokens remain exact,
including ASCII-space blanks. Numeric interpretation trims only ordinary ASCII
spaces; tabs, Unicode whitespace, commas and other unsupported syntax are not
coerced. [SAS's column-input documentation](https://support.sas.com/documentation/cdl/en/lestmtsref/63323/HTML/default/n13ejk9swz5vrbn0z34iazfrp0wp.htm)
describes blank and single-period missing fields and decimal suffixes. That
primary language reference was read on the web for this proposal; no fictitious
original-byte hash is claimed. A period is normalized to unavailable for numeric
interpretation, while its raw token remains distinct from a blank.
This is reader-language missing syntax, not a newly documented NCHS questionnaire
answer code. The classifier's documented answer-code set is unchanged.

Weight grammar permits a signed ordinary decimal literal with an optional
explicit decimal point; it does not infer a decimal position, accept exponents,
or convert through binary floating point. A finite zero or negative weight is
retained, not silently excluded. Stratum/PSU grammar permits signed integer
literals, with no guessed source range or positive-code requirement. Raw tokens
remain available, including leading zeros. Missing weight/design fields remain
unavailable and cannot silently become zero or a new design group. Unsupported
numeric syntax causes a sanitized refusal rather than a guessed recode.

For the character key, the exact seven-byte token remains private. Only outer
ASCII blanks are removed for the interpreted string; internal blanks and leading
zeros remain. A blank or single-period key is unavailable. No `HHX` prefix,
numeric conversion or unique-person interpretation is introduced. Missing keys,
repeated interpreted keys and distinct lexemes yielding the same interpreted
key remain visible in the private ledger; records are never deduplicated. A
future loader must resolve these conditions before claiming source identity or
uniqueness. This contract does not perform linkage.

Exact age codes yield a private age value; 85 yields only a lower bound of 85
and the `85_plus` category. Unknown/missing age, sex and proxy answers retain
separate groups. No proxy, unknown demographic or missing-universe record is
trimmed. The unchanged
[diagnosis classifier](../../src/demeter/data/nhis_diagnosis_labels.py) supplies its
complete seven-category response partition. Numeric period-missing is interpreted
as the classifier's missing token with the original period retained separately.
The partition describes answers, not current or latent disease states.

## Software and empirical boundaries

The pure decoder and synthetic tests return private immutable records and a
private aggregate conservation ledger. Representations omit keys, tokens and
individual field values; no public record exporter, file loader, CLI, national
estimate or clinical connection is implemented. Private handling is not an
anonymity guarantee against a caller deliberately exporting data. A future
public diagnostic requires a separately reviewed disclosure schema.

All five gates remain false: `direct_initialization_allowed`,
`clinical_fit_allowed`, `engine_activation_allowed`,
`sampling_distribution_assumed` and `scientific_release_ready`. This increment
adds no evidence parameter, source admission or empirical statistic. The source
documentation and publication summaries were examined earlier: this is used-source
development, not preregistration or independent validation of their results.

Before any real selected-value inspection, commit a reviewed contract, then admit
the exact loaded decoder/classifier/helper bytes under an independent source
guard. Bind the exact native identity, frozen acquisition/framing receipts and
schema before parsing; check framing and the resource limit first. Preserve
unknowns, missing keys, duplicates and unsupported syntax in controlled private
diagnostics; any new source-specific interpretation requires an additive reviewed
amendment, never a repair to an original. A separate empirical estimand and full
survey weight/design/interval/df/presentation policy are required before ratios.
The synthetic joint-ratio witness's positive-weight and singleton refusals do not
settle those producer or statistical choices. Total/current T2D and clinical
hazards remain unresolved.
