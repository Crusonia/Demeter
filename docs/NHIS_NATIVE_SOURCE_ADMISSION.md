# NHIS native-source acquisition and framing

Status: used-source acquisition protocol, before participant acquisition. This
increment checks the delivery of a public statistical file, not its diabetes
answers. The [frozen protocol](validation/nhis2025-native-framing-protocol-v1.json)
specifies the first permitted inspection. Source receipt hashes are not clinical
parameters or proof of a survey estimator.

The [reported-diagnosis design](design/09_NHIS_REPORTED_DIAGNOSES.md) separates
reported type from current, undiagnosed and latent diabetes. Its seven-category
software witness already preserves unknown and inconsistent answers. Before
using that interface on a source, we must establish which bytes and record
boundaries we received. This advances I-01/I-07/I-11/I-12 -> F-08 ->
T-01/T-02/T-05/T-08 and [RFC-56](rfcs/RFC-56-observation-state-mapping.md) within
the [v0.1 objective](CODEX_V0_1_OBJECTIVE.md).

## First acquisition stage

The [official 2025 catalog](https://www.cdc.gov/nchs/nhis/documentation/2025-nhis.html)
advertises a Sample Adult ASCII archive. The
[producer file list](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2025/Checksum-filelist.pdf)
names `adult25.dat`. The documentary SAS layout ends at column 685. Neither fact
proves archive membership, physical line endings, padding or final-newline rules.
The producer's displayed checksum algorithm remains unverified; we do not guess
it from the length of its token.

After this protocol is committed and reviewed, an ordinary unsigned GET may
acquire only the advertised ASCII ZIP into an ignored private source directory.
Preserve any prior receipt or original; never overwrite it. Record the literal
request and final URL, HTTP result, retrieval time, size and our SHA256. Preserve
an ordinary access failure without claiming a permanent source exclusion. Do not
use login, a guessed mirror, CSV substitution or an access workaround.

Inspect ZIP directory metadata before opening a member. Refuse unexpected,
duplicate, encrypted or unsafe members; no filesystem extraction is needed.
Cap both the downloaded archive and declared uncompressed member at 100 MiB
before reading. This is a resource limit for this workflow, not a scientific
parameter. Public metadata may name only the approved literal `adult25.dat`;
sanitize unexpected member names and omit arbitrary archive/member comments.
Reading the selected native member checks its ZIP CRC and records its own SHA256.
CRC consistency is separate from cryptographic source identity. A byte-only pass
may then record line-ending types, payload-length frequencies, final-newline
presence and ASCII validity. Do not project categorical, demographic, identifier,
weight or design fields, or run the classifier, during this stage. Emit only
technical aggregate metadata, never rows, substrings or row-level error details.

Every result is a framing observation, including an unexpected width or mixed
separator. Agreement with documentary size/count does not admit an empirical
analysis. Do not trim, pad, normalize, repair or recode an original. If framing
differs or is uncertain, retain the failure and stop before fields. Even if it is
consistent, freeze an additive source/framing receipt and a reviewed parsing
contract before any selected-value inspection. This original protocol stays
unchanged when those observations become known.

## Subsequent stages remain separate

A later source admission must bind exact ZIP and native bytes, accepted framing,
selected field positions, lexical codes, record roles and loaded parser/helper
identities. Meaningful synthetic checks must exercise wrong source bytes,
truncation, mixed separators, duplicate keys, unknown codes, privacy and complete
record conservation before the first diagnostic. No source parser is implemented
or admitted by this document.

Before an estimate, separately freeze the adult target, domains, annual weights,
full public design, unsupported-weight/singleton handling, joint covariance,
interval/df and NCHS presentation rules. Privacy is a distinct requirement. A
native format match supplies none of those scientific choices. The all-adult
recorded-answer benchmark remains the smallest candidate; age/sex domains and a
published typed-diabetes comparator are unresolved. Do not invent a numerical
acceptance tolerance or turn a metadata count into a clinical parameter.

## Rights, chronology and use

Source: CDC/NCHS. Official files are available from the agency at no charge.
Demeter and these linked materials are not endorsed by CDC, HHS or the U.S.
government. The [NCHS data-user agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html)
permits statistical reporting and analysis subject to confidentiality conditions.
Do not identify individuals, link to identifiable data or investigate disclosure
protections. The [agency materials policy](https://www.cdc.gov/other/agencymaterials.html)
requires attribution and qualification of reuse; copyright exceptions still need
specific checking. This stage keeps acquired originals private and fetch-only;
it proposes no participant-file redistribution, identity lookup or contact.

The codebook, survey description and publication summaries were already seen.
This is used-source work, not preregistration or independent outcome validation.
The protocol author and software reviewers are Codex-assisted; external domain
review is pending, with no human endorsement inferred. No participant request
had occurred when this protocol was authored.

All five gates remain false: `direct_initialization_allowed`,
`clinical_fit_allowed`, `engine_activation_allowed`,
`sampling_distribution_assumed` and `scientific_release_ready`. The runtime
model, evidence registry, raw archives and frozen reports are unchanged. A
successful acquisition would advance reproducible delivery only; total/current
T2D, transition hazards, dietary causality and national calibration remain open.
