# NHIS 2025 native delivery result

The advertised Sample Adult ASCII archive was acquired through an ordinary
unsigned request after the [acquisition protocol](NHIS_NATIVE_SOURCE_ADMISSION.md)
was reviewed and committed at `d279409f796428a94a57fe2b0a11bbe447cf377c`.
The [additive receipt](validation/nhis2025-native-framing-receipt-v1.json)
records the actual source identities and byte-only observations. The original
protocol and metadata records remain unchanged.

The archive contains one unencrypted `adult25.dat` member. Its CRC check passed;
its size and physical record count agree with the documentary file list. Every
physical record has 685 payload bytes followed by CRLF, including the final
record, and all bytes are ASCII. These are observations about these exact source
bytes, not a general framing rule inferred from the SAS layout or file size.
The producer checksum algorithm remains unverified and was not compared.

ZIP SHA256: `1981733845c4d6ede66f4756c34d47b356fbe403820c0ed33825d21e4d8f21e4`.
Native SHA256: `48b2d91002c9f30e03e87e33d37041dc991ea43a390674045a9ca60c7d004b95`.
Exact originals remain private and fetch-only; no participant file is added to
the repository. Source: CDC/NCHS, available without charge from the
[official catalog](https://www.cdc.gov/nchs/nhis/documentation/2025-nhis.html).
Demeter is not endorsed by CDC, HHS or the U.S. government.

No identifier, diagnosis, demographic, weight or design field was projected.
No classifier or survey calculation ran on participant values. A source parser,
record/lexical contract and independent loaded-code admission still need review
and synthetic verification before any diagnosis diagnostic. A separate estimand,
survey/presentation contract and disclosure policy remain necessary before an
empirical estimate. File delivery does not settle those requirements.

The executable acquisition utility was reviewed and tested with synthetic
transport/privacy refusals before the real request; its exact executed bytes are
identified in the receipt. Those checks establish a technical inspection only,
not admission of a clinical calculation. The receipt's source and code hashes
identify this acquisition; they must not be substituted for future parser/code
admission. No model parameter or equation changed. All five scientific gates
remain false, and reported type cannot initialize total or current T2D.
