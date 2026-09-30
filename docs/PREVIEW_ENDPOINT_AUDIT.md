# PREVIEW: what a normal-glucose visit can tell us

This audit reproduces a small, public set of PREVIEW trial results and shows how
unobserved outcomes limit interpretation. It is **used-source reproduction**, not
independent validation: the publications and results were inspected before the
analysis specification was frozen. It does not fit a clinical transition, change
a dietary coefficient, or establish a healthcare-cost forecast.

The [frozen specification](validation/preview-endpoint-protocol-v1.json),
[clarification amendment](validation/preview-endpoint-amendment-1.json),
[inspection chronology](validation/preview-inspection-chronology-v1.json), and
[source receipts](validation/preview-source-receipts.json) preserve what was
selected, what had already been seen, and which exact source bytes were used.

The [verified context amendment](validation/preview-endpoint-context-amendment-3.json)
was frozen after the first reproduction to address a review finding. It pins six
source facts: visit windows, nominal assessment weeks, run-in duration, and the
reported confidence level. The corrected audit checks their registry values and
provenance against these frozen expectations. It verifies source-file hashes;
it does not independently re-extract the PDF context facts during runtime. Those
facts were separately checked against the pinned primary documents. This review
fix preserves the original freeze, analytical selection, and numerical endpoint
outputs.

## Who and what were studied

PREVIEW recruited adults with overweight or obesity and screening-defined
prediabetes. Everyone first received a common eight-week low-energy weight-loss
programme. Only successful weight-loss responders continued into maintenance.
The four groups combined two diet assignments with two physical-activity
assignments. Assignment occurred before the common initial phase; allocation was
concealed until maintenance began. Sources: [2017 design report,
sections 2.3–2.5](https://doi.org/10.3390/nu9060632) and [original 2021 report,
section 2.6](https://doi.org/10.1111/dom.14219).

The diet comparison pools both activity assignments within each diet. The diets
combine differences in protein, carbohydrate quantity, glycaemic index, and food
guidance; both receive behavioural support. This is not an isolated protein,
ingredient, or ultra-processed-food experiment. The common weight-loss phase has
no comparison that would identify its own causal effect.

Responder selection occurs after assignment, but before the disclosed
maintenance regimen. It need not destroy randomization if concealment held, the
initial programme was identical, and selection was unaffected by assignment.
That would justify a maintenance-eligible target cohort; it does not make this a
comparison for everyone originally recruited. Missing follow-up outcomes remain
a separate problem. Adherence assumptions are needed to estimate consumed-dose
or as-treated effects, rather than automatically for an assignment-strategy
effect.

## What the endpoint measures

The [secondary report's Outcomes section](https://link.springer.com/article/10.1007/s00125-025-06560-x#FPar4)
defines the endpoint as normal fasting glucose **and** normal two-hour glucose
after an oral glucose tolerance test at the specified visit. The source cutoffs
are fasting glucose below 5.6 mmol/l and two-hour glucose below 7.8 mmol/l. These
define this source measurement endpoint; they do not assign Demeter's clinical
states.

Year 1 and year 3 are separate snapshots. A person might normalize during the
initial programme, later become abnormal, then test normal again. Two aggregate
snapshots cannot tell that history apart from continuous normality. They also do
not establish a medication-free interval, repeated confirmation of remission, or
the removal of an earlier diabetes diagnosis. The audit therefore calls this a
**normal-glucose endpoint**, while retaining the paper's “prediabetes remission”
label in source locators.

Nominal week 52 and week 156 are explicit visit-schedule labels in the
[original 2021 report, section 2.1 Participants](https://doi.org/10.1111/dom.14219),
physical PDF page 3 / printed page 326. They include the initial eight weeks and
are measured from study baseline; exact randomization and baseline dates must not
be equated. The original report describes withdrawals between them. The
[2017 protocol, section 2.6](https://doi.org/10.3390/nu9060632), physical PDF page 8 /
printed page 7, supplies the visit windows: ±2 weeks at year 1 and ±4 weeks at
later assessments. That paragraph supplies the windows, not the nominal week
labels. Actual participant dates and window adherence are unavailable in these
aggregate cells.

## Keep three denominators separate

For each diet and assessment:

- **N** is the selected maintenance cohort in the main secondary report.
- **n** is the denominator of the published normal-glucose endpoint cell.
- **y** is the number classified normal in that cell.

The first frozen reproduction uses these literal main-source counts only. They
are reported observations, not newly inferred outcomes. N does not change
between the two assessments.

| Nominal assessment | Assigned maintenance diet | Selected cohort N | Endpoint denominator n | Normal count y |
| --- | --- | ---: | ---: | ---: |
| Year 1 | Moderate protein / moderate GI | 923 | 604 | 159 |
| Year 1 | High protein / low GI | 933 | 646 | 134 |
| Year 3 | Moderate protein / moderate GI | 923 | 472 | 97 |
| Year 3 | High protein / low GI | 933 | 471 | 73 |

Primary locators: [Results → Participants, first paragraph](https://link.springer.com/article/10.1007/s00125-025-06560-x#FPar6)
for N; [Results → Prediabetes remission, first paragraph](https://link.springer.com/article/10.1007/s00125-025-06560-x#FPar8)
for y/n. The pinned HTML uses `#Sec3-content`, heading IDs `FPar6` and `FPar8`;
Figure 1's description is `#figure-1-desc`.

Attendance, completion of the whole study, and availability of this endpoint are
different measures. Do not replace n with a completer count. **N−n means an
unclassified endpoint**, not a verified dropout, missed test, death, or diagnosis.
Unknown medication history in an assessed person does not increase N−n; it
limits the clinical meaning of that person's endpoint.

## Raw proportions and adjusted estimates answer different questions

The count-derived proportion is:

```text
p_observed[diet, visit] = y / n
```

It describes people in the source endpoint denominator. The absolute observed
contrast is the moderate-protein proportion minus the high-protein proportion.
Multiply a difference in fraction units by 100 to display percentage points.
Neither calculation corrects for unobserved outcomes.

The paper also reports adjusted relative risks:

| Assessment | Published adjusted RR, moderate versus high protein | Published 95% CI |
| --- | ---: | --- |
| Year 1 | 1.26 | 1.04–1.53 |
| Year 3 | 1.26 | 1.06–1.50 |

These come from multilevel modified Poisson models with sex and age-group fixed
effects and a centre random effect. The counts cannot reconstruct that fitted
model. Its adjusted RR need not equal the ratio of the raw proportions. The
published intervals remain source-model uncertainty; they are not new intervals
calculated by this audit. See [Statistical analysis](https://link.springer.com/article/10.1007/s00125-025-06560-x#FPar5)
and [Figure 1](https://link.springer.com/article/10.1007/s00125-025-06560-x#Fig1).

These are visit proportions and relative risks, not annual transition hazards.
The two visits reuse participants, but the public marginal counts do not provide
their joint histories or covariance. The audit analyzes each visit separately.

## What the missing-outcome envelope means

Suppose every unclassified endpoint were assigned a binary label solely for a
mathematical sensitivity check. The lowest completed proportion assigns all
unclassified labels zero; the highest assigns them all one:

```text
m = N - n
lower = y / N
upper = (y + m) / N

contrast_lower = lower[moderate protein] - upper[high protein]
contrast_upper = upper[moderate protein] - lower[high protein]
```

These extremes add no observed cases and assume no missing-at-random model.
They show how much room is left when the unknown labels are allowed to differ
between diets. They are **deterministic completion envelopes**, not confidence
intervals, credible intervals, or a forecast of what happened to missing people.
If the contrast envelope includes zero or both directions, report that the
completions do not identify direction. Do not select assumptions to remove that
possibility.

Survival and treatment remain unresolved. The upper completion does not assert
that everyone survived or recovered. A verified death before assessment could
be zero only in a separately defined **alive-and-normal composite**; death is
never a normal or abnormal glucose state. These main cells supply no verified
death classification. Clinical-composite, survivor, and untreated-remission
interpretations remain unavailable.

## A worked year-3 example

The first source audit passed all four byte checks and matched the frozen main
cells. The following are **count-derived, used-source calculations**, rounded
for display:

| Assigned diet | Observed endpoint y/n (%) | Selected-cohort label-completion extremes (%) |
| --- | ---: | --- |
| Moderate protein / moderate GI | 97/472 = 20.55 | 10.51–59.37 |
| High protein / low GI | 73/471 = 15.50 | 7.82–57.34 |

The observed difference is **5.05 percentage points**. The completion contrast
ranges from **−46.83 to +51.55 percentage points**, allowing either direction.
This shows how much unobserved endpoint labels can matter. It does not estimate
what missing people experienced, assert survival, or identify a causal dietary
effect. The published adjusted RR/CI addresses a different model-based question;
its interval must not be substituted for this completion envelope.

## Disagreements and failures stay visible

The audit preserves the source population's fasting-glucose **and/or** OGTT
eligibility wording and the different **and** wording in its Outcomes paragraph.
The original design uses `>8%` weight-loss eligibility; later reports use `≥8%`.
Neither discrepancy is silently reconciled. HbA1c was not a screening eligibility
measure, and screening exclusion does not establish complete biochemical or
diagnosis history. See [ESM methods, pages 1–2](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs00125-025-06560-x/MediaObjects/125_2025_6560_MOESM1_ESM.pdf).

ESM page 8, Table 1, has completer/header counts that conflict with the main
selected cohort and table-body counts. It is retained as an unresolved source
discrepancy, rather than used to repair the main endpoint denominators. Original
and secondary auxiliary first-diabetes analyses also remain separate. The
original primary diabetes-incidence report found no statistically significant
dietary difference; this does not prove a zero effect. A normal-glucose endpoint
and first diabetes diagnosis are different outcomes. See
[ESM Table 1, page 8](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs00125-025-06560-x/MediaObjects/125_2025_6560_MOESM1_ESM.pdf)
and the [original report](https://doi.org/10.1111/dom.14219).

The earlier [context amendment](validation/preview-endpoint-context-amendment-2.json)
is retained as a superseded review record: it attributed the nominal week labels
to the wrong protocol paragraph. No corrected audit or numerical reproduction
ran with that disputed amendment. The exact week labels were verified in the
original 2021 report before the replacement context amendment was frozen; the
earlier record and original analysis files remain intact.

Changed source bytes or a failure to match a frozen literal cell stops source
reproduction. Do not reconstruct counts from rounded percentages, replace a
source silently, or change the frozen specification to make an audit pass.
Unreconciled denominators block the selected-cohort envelope as needed. Missing
death, medication, confirmation, and timing information block clinical
interpretation even when arithmetic passes.

## Run the audit

Start in the repository root after following the platform setup in
[Getting Started](GETTING_STARTED.md). The Python engine and this CLI do not require a web
server. Install the project environment once:

```text
uv sync --locked
```

Use the public source cache to reproduce the frozen cells:

```text
uv run demeter evidence preview-endpoints --raw outputs/public-source-search-20260930 --output outputs/preview-endpoints.json
```

The report is written to the named output path. Inspect its source checks and
limitations alongside its arithmetic. A success establishes the declared
reproduction checks; it does not remove the clinical limitations above.

### Fetch the four public documents without replacing existing bytes

The following commands use only the public document URLs in the committed
receipts. They do not request participant records. Full documents stay in the
ignored `outputs` cache and must not be added to a commit, wheel, or exported
report. The secondary article/ESM are CC BY 4.0 with third-party exceptions;
other sources retain their own terms. The secondary paper offers participant
datasets through a reasonable request to the corresponding author rather than
providing an unrestricted public download; this workflow makes no request or
contact.

**Windows PowerShell**, from the repository root:

```powershell
@'
import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

protocol = json.loads(Path("docs/validation/preview-endpoint-protocol-v1.json").read_bytes())
receipts = json.loads(Path("docs/validation/preview-source-receipts.json").read_bytes())["receipts"]
raw = Path("outputs/public-source-search-20260930")
raw.mkdir(parents=True, exist_ok=True)
for pin in protocol["source_bytes"]:
    target = raw / pin["file"]
    if not target.exists():
        url = receipts[pin["receipt_key"]]["requested_url"]
        started = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(url, headers={"User-Agent": "Demeter public-document audit"})
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
            receipt = dict(url=url, final_url=response.url, status=response.status,
                           content_type=response.headers.get("Content-Type"),
                           started_utc=started, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                           size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        with target.open("xb") as stream:
            stream.write(content)
        with target.with_name(target.name + ".local-fetch.json").open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
    content = target.read_bytes()
    matches = len(content) == pin["size_bytes"] and hashlib.sha256(content).hexdigest() == pin["sha256"]
    print(target.name, "matches frozen bytes" if matches else "PIN MISMATCH: retained for review")
'@ | uv run python -
uv run demeter evidence preview-endpoints --raw outputs/public-source-search-20260930 --output outputs/preview-endpoints.json
Get-Content outputs/preview-endpoints.json
```

**macOS or Linux**, from the repository root:

```bash
uv run python - <<'PY'
import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

protocol = json.loads(Path("docs/validation/preview-endpoint-protocol-v1.json").read_bytes())
receipts = json.loads(Path("docs/validation/preview-source-receipts.json").read_bytes())["receipts"]
raw = Path("outputs/public-source-search-20260930")
raw.mkdir(parents=True, exist_ok=True)
for pin in protocol["source_bytes"]:
    target = raw / pin["file"]
    if not target.exists():
        url = receipts[pin["receipt_key"]]["requested_url"]
        started = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(url, headers={"User-Agent": "Demeter public-document audit"})
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
            receipt = dict(url=url, final_url=response.url, status=response.status,
                           content_type=response.headers.get("Content-Type"),
                           started_utc=started, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                           size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        with target.open("xb") as stream:
            stream.write(content)
        with target.with_name(target.name + ".local-fetch.json").open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
    content = target.read_bytes()
    matches = len(content) == pin["size_bytes"] and hashlib.sha256(content).hexdigest() == pin["sha256"]
    print(target.name, "matches frozen bytes" if matches else "PIN MISMATCH: retained for review")
PY
uv run demeter evidence preview-endpoints --raw outputs/public-source-search-20260930 --output outputs/preview-endpoints.json
cat outputs/preview-endpoints.json
```

Publishers can change HTML wrappers or document versions. A fresh download may
therefore fail the frozen byte check. Preserve it and its local receipt for
maintainer review; do not overwrite earlier bytes or edit the source pin.
Network/download failures also leave the source check incomplete.

## What this advances, and what remains open

[#57](https://github.com/Crusonia/Demeter/issues/57) still requires compatible
clinical transition evidence and an identifiable observation model.
[#58](https://github.com/Crusonia/Demeter/issues/58) still requires evidence that
identifies the dietary pathway and its effects. This audit supplies a reproducible
measurement endpoint and a transparent account of missingness; it does not
identify annual progression/recovery hazards, a consumed dietary dose, an effect
lag, mortality, U.S. transport, or the active engine's UPF coefficient.

The [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) explains
the individual or sufficient aggregate histories needed next: compatible
starting states, linked repeated tests and confirmation, exposure and treatment
timing, missing-test/contact history, and competing events. Independent validation
would also require evidence not already used for this source-specific design.

This is one incremental step toward the health slice in the
[project vision](PROJECT_VISION.md). Educational model exercises can make
assumptions inspectable today; their scenarios become clinical or economic
evidence only when the corresponding observations, identification, uncertainty,
and validation requirements have been met.
