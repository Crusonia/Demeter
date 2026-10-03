# NHANES III repeat fasting-glucose observations

Before treating one laboratory measurement as a lasting metabolic state, Demeter
checks whether a source's recorded glucose label persists at its designated repeat
examination. This step informs the observation model. It does not establish how
diet changes disease, health-care costs or longevity.

This resource is **NHANES III, 1988–1994**, a historical U.S. survey. It is separate
from the [2021–2023 assay comparison](NHANES_ASSAY_OBSERVATION_MAPPING.md). The repeat sample
was not a representative survey subsample and has no dedicated survey weight.
Its result cannot be presented as a national prevalence or a modern assay
calibration.

## What the check means

The [first admitted public report](validation/nhanes3-repeat-fpg-report-v1.json)
has status `contradicted`: the literal recorded-label persistence premise fails
within the declared finite subset. This does not establish why labels changed,
diagnose remission, or estimate how often a clinical state changes nationally.
Missing observations and eligibility clauses remain in the private conserved
ledger; they are never replaced with negative assay values.

Replay the committed originals offline on Windows, macOS or Linux:

```console
uv run demeter evidence nhanes3-repeat-fpg
uv run python scripts/verify_nhanes3_repeat.py
```

No network or new download is needed for either command. The CLI emits only the
coarse admitted public result. Use `--output outputs/repeat-fpg.json` to save a
new copy; existing files and source/evidence/documentation paths are refused.
The verifier reproduces every public field except the explicitly identified
registry fingerprint, which may change when unrelated evidence is added.

The narrowly scoped question is whether every qualifying first fasting plasma
glucose (FPG) measurement at or above 126 mg/dL also has that recorded label in
its linked, designated repeat record. Here, **positive means a recorded threshold
label, not diagnosed diabetes**. A counterexample can refute that literal
persistence claim. Without a qualifying pair or any first-positive pair, the
question is not evaluable; an empty sample cannot pass.

The subset requires primary mobile examination center (MEC) age of at least
20 years, literal `HAD1 == 2`, at least eight recorded fasting hours at both
examinations, supported session codes and two supported, positive FPG values.
The producer's `No` response includes borderline diabetes or prediabetes. It
does not establish complete lifetime diagnosis history. Treatment and screening
fields are omitted from eligibility, so this is **not a treatment-free sample**
or a reproduction of the published Selvin study cohort.

The laboratory fields and producer procedure descriptions support a declared
MEC-context interpretation. They do not independently establish each person's
specimen location or blood-draw session. Primary session can mean the session
when most examinations were completed. The age topcode `1080` means **1080 or
more months**, rather than an exact age of 90 years.

Recorded examination days are kept separately from eligibility. Missing or
none/never clocks remain unknown; a positive value does not prove forward
biological order. The diagnostic concerns designated repeat labels, not a
transition rate or a timed clinical process. Measurement variation, temporary
biological changes and other changes between examinations cannot be separated
using these two assays alone.

## Obtain source originals

The official [NCHS catalog](https://wwwn.cdc.gov/nchs/nhanes/nhanes3/datafiles.aspx)
provides the three native files freely:

| Original | Role | Official download |
| --- | --- | --- |
| `LAB.DAT` | First laboratory record and MEC context | [LAB](https://wwwn.cdc.gov/nchs/data/nhanes3/1a/lab.dat) |
| `ADULT.DAT` | Recorded diabetes-history response | [ADULT](https://wwwn.cdc.gov/nchs/data/nhanes3/1a/adult.dat) |
| `LABSE.DAT` | Designated repeat laboratory record | [LABSE](https://wwwn.cdc.gov/nchs/data/nhanes3/3a/labse.dat) |

The original source files and their admitted manifest are included in the
repository. For a separate acquisition in a fresh reviewed destination, after
[installing the development environment](../README.md), use the same explicit
command on Windows, macOS and Linux:

```console
uv run python scripts/fetch_nhanes3_repeat.py --download --destination outputs/nhanes3-new-originals
```

The command requires the exact committed
[intake protocol](validation/nhanes3-repeat-intake-protocol-v1.json) in both the
checkout and its current Git head. It records that invocation commit separately
from the original protocol-authoring commit; a shallow or squash clone does not
need that historical commit object to acquire the same source URLs. It acquires original bytes into
`data/sources/nhanes3/1988-1994-repeat/` and records source URLs, retrieval times,
byte sizes, SHA-256 hashes and transport receipts. It prints receipt metadata,
never participant records. It does not run the observation diagnostic.

An existing store is refused even if empty or incomplete. The downloader
reserves a new directory exclusively, writes each original exclusively and
writes `manifest.json` last. This is **not atomic whole-store publication**.
If a request fails, the partial store remains available for review. Receipt
attempts for repository data destinations are retained under
`outputs/nhanes3-acquisition/`; custom destinations outside data use a sibling
`.attempt-*` directory. Do not replace partial files, silently repair the
store or claim that an incomplete download is admitted evidence. Preserve the
attempt and resolve its failure before using a separately reviewed destination.

A fresh fetch has its own retrieval identity. It does not replace the archived
v1 manifest or source-admission receipt. Strict v1 offline replay requires the
original admitted source bytes, manifest and retrieval identities.

The acquisition utility checks bounded, ordinary public transport and preserves
the original bytes. Independent raw-source admission and the separately scoped
framing check must happen before selected study values are decoded. Download
success alone does not authorize a model fit or establish a scientifically valid
diagnostic. No survey weights are used in this finite observation check.

## What can be published

The committed contract retains complete private eligibility and observation
ledgers. Public output is deliberately coarse: provenance, inactive gates,
source-audit and conservation indicators, and a diagnostic status when the
disclosure rule permits it. It excludes participant keys, assay values, paired
cells, margins, support counts and reasons for withholding. Singleton and
delete-one isolation checks can withhold the status; they do not discard people
from the private calculation or provide a blanket anonymity guarantee.

All five scientific gates remain false: direct initialization, clinical fitting,
engine activation, an assumed sampling distribution and scientific release.
The [reviewed design record](https://github.com/Crusonia/Demeter/blob/9beccbd93e9404e6e26f2771d8c6926a152e9082/docs/design/08_NHANES_III_REPEAT_OBSERVATIONS.md) and
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) explain the
next validation steps. The source protocol is used-source development: papers,
metadata and published results were examined before it was written. It is not
preregistration or an independent holdout.

## Producer documentation and reuse notice

Definitions and native column positions come from the NCHS
[repeat README](https://wwwn.cdc.gov/nchs/data/nhanes3/3a/readme.txt),
[LAB codebook](https://wwwn.cdc.gov/nchs/data/nhanes3/1a/lab-acc.pdf),
[ADULT codebook](https://wwwn.cdc.gov/nchs/data/nhanes3/1a/ADULT-acc.pdf) and
[LABSE codebook](https://wwwn.cdc.gov/nchs/data/nhanes3/3a/LABSE-acc.pdf).
Important locators include LAB pages 66–67 and 106 for session and MEC age,
ADULT page 171 for `HAD1`, and LABSE pages 10–11, 39, 42 and 65 for repeat
selection, session, clock, fasting and FPG. Printed observed ranges are not
parser validity limits. The [documentation receipt artifact](validation/nhanes3-repeat-documentation-receipts-v1.json)
preserves the inspected documentary identities and locators.

The age, fasting and threshold criteria are traced to the methods of
[Selvin et al., 2007](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/412871),
DOI 10.1001/archinte.167.14.1545; they are fixed subset definitions, not fitted
effects. Ordinary publisher acquisition returned an access refusal during
design review, so Demeter does not claim an archived publisher-byte reproduction.

Demeter acknowledges **CDC/NCHS** as the source. Follow the official
[NCHS data-user agreement](https://www.cdc.gov/nchs/policy/data-user-agreement.html)
and [CDC agency-materials policy](https://www.cdc.gov/other/agencymaterials.html).
Originals are available free at the official URLs. Demeter's use of these sources
or links does not imply endorsement by CDC, HHS or the U.S. government.
