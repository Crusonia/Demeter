# Public iPOP linked laboratory intake

The pinned public derivative contains repeated laboratory observations suitable
for developing a conditional native-cohort analysis. This intake checks source
integrity, association rules and numerical availability. It estimates no clinical
transition, dietary effect, mortality rate or national model parameter.

## Run it

After the [project setup](../README.md), run these commands from the repository
root. They work in PowerShell on Windows and in a macOS/Linux terminal:

```bash
uv run demeter data fetch-ipop --destination data/raw/ipop-v1
uv run demeter evidence ipop-preflight --raw data/raw/ipop-v1 --output outputs/ipop-exact-v1.json
uv run demeter evidence ipop-crosswalk-preflight --raw data/raw/ipop-v1 --output outputs/ipop-crosswalk-v2.json
```

The first command downloads exactly two frozen public files. It creates checked
ignored parent directories and a fresh cache with immutable acquisition receipts.
No account or access agreement is needed for this selected public derivative.
The evidence commands verify receipts and complete bytes offline before parsing.
They save and display aggregates, without participant identifiers, assay values,
day values, partner lists or individual trajectories.

The destination leaf and report files must not already exist. To replay a saved
cache, omit the download and choose new output filenames. Existing source and
report bytes are never replaced. Do not commit the raw cache; it is fetch-only.
`uv run demeter data verify-packages --check-tracked` checks registered hashes and
rights metadata; it does not fetch or validate your cache.

## What the actual intake found

Complete files were acquired on October 1, 2026. These are exact diagnostics for
the pinned bytes, not population estimates or uncertainty intervals. The
[acquisition receipts](validation/ipop-preflight-acquisition-receipts-v1.json)
record both successful requests. A [history record](validation/ipop-preflight-acquisition-history-v1.json)
preserves an earlier local directory failure before any network request.

| Diagnostic | Count | Meaning |
| --- | ---: | --- |
| Clinical source rows | 969 | Every selected source row remains in the denominator. |
| Metadata source rows | 1,092 | Includes rows without a matching clinical test. |
| Clinical rows with finite A1C tokens | 956 | Numerical availability without clinical-state certification. |
| Clinical rows with finite GLU tokens | 963 | GLU is not silently relabeled fasting plasma glucose. |
| Literal v1 admitted rows | 0 | Raw subject tokens differ across files. |
| V2 mutually consistent unique sample associations | 951 | Conditional on the producer sample-association assumption. |
| V2 unmatched clinical sample keys | 16 | Retained outside linked coverage. |
| V2 clinical rows with ambiguous metadata sample keys | 2 | Retained and excluded from admitted observations. |
| V2 admitted metadata subject labels | 104 | Source labels, not certified participant identities. |
| Labels with A1C at multiple distinct finite day coordinates | 94 | Ten other admitted labels have one coordinate. |
| Labels with GLU at multiple distinct finite day coordinates | 94 | Same assay-specific denominator and interpretation. |

All 951 admitted rows have finite day tokens; 938 have finite A1C and 945 have
finite GLU. No admitted row shares its metadata subject label and finite day
coordinate with another admitted row. This does not prove specimen dates,
fasting status, raw assay units, biological onset or an ignorable visit process.

## Why there are two results

The [v1 numerical protocol](validation/ipop-numerical-preflight-protocol-v1.json)
was committed and pushed at `ab69c5f` before complete acquisition and aggregation.
It required literal clinical/metadata SubjectID equality alongside a unique
VisitID-to-SampleID match. The [original result](validation/ipop-preflight-exact-subject-v1.json)
is unchanged: 951 unique sample matches have unequal subject tokens, so no
literal-equality panel is admitted. Zero admitted rows means this rule failed;
it does not mean nobody was followed or that participants died.

The producer's pinned notebooks discard clinical SubjectID and join by SampleID
to metadata subject/day records. That supports a separate association hypothesis,
without explaining or certifying the raw subject namespaces. The
[v2 protocol](validation/ipop-namespace-crosswalk-protocol-v2.json) was committed
and pushed at `36294db` after seeing v1 but before computing the namespace graph
or v2 coverage. This is adaptive, used-source research, not preregistration or
independent validation.

V2 constructs the full observed partner graph using all exact sample matches
with available subject tokens. Ambiguous right-hand keys contribute possible
partners before eligibility or assay/day filtering. A row is admitted only if
its sample match is unique and each subject label has exactly one observed
partner in its respective namespace. There is no lexical equality bypass,
normalization, iterative edge removal or duplicate averaging. Every source row
remains accounted for.

The graph contains 104 distinct possible pairs. All 104 clinical subject labels
have one observed partner; of 106 metadata labels, 104 have one and two have none.
That establishes consistency within the available records. A consistently wrong
bijection remains possible; unknown partners are not ruled out. Coverage groups
by metadata SubjectID under the declared producer association assumption.

The [actual v2 result](validation/ipop-preflight-namespace-result-v2.json) embeds
the complete pure v1 report and reproduces all original v1 numerical sections.
Its wrapper separately verifies receipts. The nested pure report's receipt flag
remains false because the pure function does not read receipts; the top-level
acquisition audit supplies that additional verification.

## Source and interpretation

Source: [Zheng et al. (2022)](https://doi.org/10.1038/s41598-022-16326-9) and its
[TemporalMultiomicsDiabetes repository](https://github.com/gmiaslab/TemporalMultiomicsDiabetes),
commit `ba55996cb51a8bc4fbe9374633e9cb3223c6ea8c`.

| File | Complete bytes | SHA256 |
| --- | ---: | --- |
| `data/clinical_tests.txt` | 231,694 | `94bca4d56dcb96e83a780479c5e23610e366060bcc8607f67377378d3fc39f52` |
| `data/SampleInfo.csv` | 36,407 | `7e9026e13f0cf105ade8429e40c5f5ca4adaa248f4552f32a71fa4327c3e4a3e` |

Credible author-declared public lineage supports this bounded intake. Original
CC0 provenance, the derivative's MIT code license and scientific interpretation
remain distinct. Complete participant files stay in ignored storage; only
attributed aggregate diagnostics are distributed. See the
[source appraisal](IPOP_SOURCE_COVERAGE.md) and [rights inventory](../data/rights.json).

HbA1c percent, a separately declared GLU fasting interpretation, assay rawness and
the relative-day specimen clock remain explicit assumptions. An unknown additive
time origin cancels in within-person elapsed differences; it does not alone
disqualify that analysis. Units are never inferred from value ranges.
Undocumented tokens are not guessed missing. CollectionDate and unselected
fields remain opaque. The selected CL4 tokens remain opaque context; their
presence or equality does not identify illness versus scheduled visits. No
observation-process model is selected by this intake.

## Next model-design step

Specify a native-cohort laboratory-proxy estimand and observation likelihood using
these repeated observations. Compare measurement and visit-selection assumptions;
retain missing tests, treatment/diagnosis uncertainty and stopping limitations.
Assess identification and joint uncertainty before interpreting a fit. Any
evaluation split must disclose prior source use for intake.

Laboratory labels do not supply confirmed diagnosis or remission. Death,
withdrawal, missed-visit denominators, last contact and administrative stopping
remain unknown; no dependent mortality/censoring claim is supported. This panel
does not identify an isolated dietary effect or justify national transport.
[Issues #57 and #58](PUBLIC_EVIDENCE_ROADMAP.md) remain open. All 146 existing
model parameters are unchanged, and active simulations remain validation-only.

The [simulation preservation receipt](validation/ipop-intake-simulation-preservation-v1.json)
checks three canonical scenarios and all parameter definitions. Registering new
sources changes the complete registry fingerprint. The
[historical report replay receipt](validation/ipop-historical-report-replay-v1.json)
confirms that three older observation reports reproduce every other field
exactly. Their original bytes and historical fingerprints remain unchanged.
