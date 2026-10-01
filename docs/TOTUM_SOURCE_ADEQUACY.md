# TOTUM63: can the public source preserve the observations we need?

This audit asks whether a small part of the public TOTUM63 workbook can be read
without losing its meaning. It checks source bytes, headers, cell types and
layout. The implementation and first aggregate audit are available. All five
source byte pins and selected headers passed; clinical adequacy remains
unresolved. This does not estimate an effect, classify diabetes, or fit a
clinical transition. See the [aggregate audit](validation/issue-57-58-totum-source-adequacy.json)
and [design RFC](rfcs/RFC-57-58-totum-source-adequacy.md).

The [selection contract](validation/totum-source-row-protocol-v1.json) was committed
before numerical outcome-row inspection. Methods, access metadata and headers
had already been inspected. This is a methods-informed source audit, not trial
preregistration or independent validation. The [historical source receipts](validation/totum-source-row-receipts-v1.json)
identify the original acquisitions. A separate Codex source critique found no
blocking factual issue after the recorded clarifications; external human clinical
assessment remains pending.

## A row is a source observation, not automatically a person

The selection is **Table 4, columns A:D, starting at row 5**. All selected rows
remain in scope, including rows labelled for the exploratory open-label BID arm.
The source headers describe A as group, B as glycemic status, C as baseline FPG,
and D as six-month FPG, in mg/dL. FPG means fasting plasma glucose.

Two measurements beside one another establish a layout relationship. They do
not independently verify that both belong to one person, that every person
occurs once, or that the rows cover everyone randomized. The audit preserves
that relationship without creating participant IDs, joining sheets, filling
group labels down, or interpreting B as a diagnosis.

Chavanelle et al. (2026) studied sites in France, Germany, Italy, Bulgaria,
Hungary, Poland and Romania ([Study design](https://www.nature.com/articles/s41467-026-75626-0#Sec15),
Procedures, and registration locations); the selected rows do not identify site.
The trial included a blinded TID comparison and an exploratory open-label BID arm,
with common lifestyle guidance. The primary endpoint was
the between-group difference in FPG change. The methods schedule the final visit
at **24 weeks ±5 days**; the worksheet labels it **6 months**. Neither label
supplies an actual collection date. See primary [Procedures](https://www.nature.com/articles/s41467-026-75626-0#Sec18)
and [Outcomes](https://www.nature.com/articles/s41467-026-75626-0#Sec20).

## What the first aggregate audit establishes

A positive finite number is numerical availability, not certification of a
valid fasting assay. Zero, negative and nonfinite numbers remain separate from
absent cells, explicit blanks, text, errors, dates, booleans and formulas.
Numeric-looking text is not silently converted; formulas are not executed.
An all-empty layout row is not counted as a lost participant.

The report may count raw cell types, same-row C/D type combinations, empty rows,
merges and recognized group labels. Unexpected text and source glycemic-status
labels are not exported. It exports no individual glucose values, participant
rows, means, changes, clinical categories or treatment comparisons. Passing
integrity checks means the selected bytes and layout agree with the contract;
clinical adequacy is still unresolved.

| Selected source coverage | Count |
| --- | ---: |
| Source positions / nonempty positions | 636 / 636 |
| C: numeric / explicit blank | 635 / 1 |
| D: numeric / explicit blank | 606 / 30 |
| Same-position C/D: numeric / numeric | 605 |
| Same-position C/D: numeric / blank | 30 |
| Same-position C/D: blank / numeric | 1 |
| All-empty A:D layout positions | 0 |

Both group and status columns contain 636 text cells. Reviewed group labels
occur as PBO 210, T63 TID 212 and T63 BID 214; these are source-token frequencies.
The same-position counts reconcile with the separate C/D totals. They do not
show 605 people with valid paired assays or 30 withdrawals. Every numeric FPG
cell is positive finite, but clinical validity remains unverified. Verified
participant and clinical-pair counts are `null` (unknown). Zero all-empty rows
does not establish zero loss, death or missing visits.

## Sources, pins and unresolved differences

These five public URLs are the exact requested URLs in the frozen receipts.
Full source files are **fetch-only**: keep them in ignored local storage, outside
commits and public reports. The workbook release is version 1 under CC BY 4.0;
the publication and registry sources retain their own terms.

| Source | Requested public URL | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Figshare release metadata | [Article API](https://api.figshare.com/v2/articles/32348169) | 6487 | `5088646d5cde5ea9948464f64bc306a3a3547e9aa6e7b5207a8b7e04ba2367d7` |
| Primary paper | [Nature Communications](https://www.nature.com/articles/s41467-026-75626-0) | 389951 | `3aa274b1bc02e211c934050be4b623d01325c3fd7d72eda2b21e9d3dcd67733b` |
| Reporting summary | [Publisher PDF](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-026-75626-0/MediaObjects/41467_2026_75626_MOESM2_ESM.pdf) | 8112598 | `551746cead8181c483bcdd4f08d96ffe609571a5cdce7a6249663f476ca54e34` |
| Trial registration | [NCT04423302 API](https://clinicaltrials.gov/api/v2/studies/NCT04423302) | 29502 | `9db0a51e0d91eba2bb60dd58114a4401a5501e26454ebfdecbd57725e116b7e7` |
| Public workbook | [Figshare file 65557542](https://ndownloader.figshare.com/files/65557542) | 501221 | `a86dbc63fcd4f4d9f8906d3a14bcd16b1b6bb38d19e1e30825faed0b1827ba2d` |

The paper's [data-availability statement](https://www.nature.com/articles/s41467-026-75626-0#data-availability)
advertises all collected deidentified participant data. Reporting Summary p. 1
routes clinical data through requests and describes public tables/figures data;
the cached registration says IPD sharing is `NO`. These differences remain
visible. They do not revoke the verified public workbook license or establish
its participant coverage. No contact or record request is part of this audit.

Reporting Summary p. 2 says no data were excluded; that does not establish complete
visits. Its p. 5 and the paper's Outcomes describe omitted later follow-up and
pharmacotherapy-requirement timing. The registration defines the latter through
investigator withdrawal. Actual treatment, stopping, loss and death histories
remain unknown. The paper's [Statistics](https://www.nature.com/articles/s41467-026-75626-0#Sec25)
uses patient/center effects and an imputation sensitivity analysis; this intake
neither reconstructs that model nor carries a last value forward. Registration
and paper category definitions also differ; no category conversion is attempted.

## Set up and obtain the source safely

Follow [Getting started](GETTING_STARTED.md) for Windows, macOS or Linux. From the
repository folder, run `uv sync --locked`. If the five pinned files are already
in `outputs/public-source-search-20260930`, skip fetching and use the audit command
below. Otherwise, copy the fetch block for your terminal. It creates a fresh
ignored directory, never replaces frozen caches, and writes new acquisition
receipts with actual UTC times. New receipts are separate from historical ones.

The following entire block works in Windows **PowerShell** and macOS/Linux
**Terminal**. Paste it from the repository folder (not Windows Command Prompt):

```text
uv run python -c "
import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
now = lambda: datetime.now(timezone.utc).isoformat()
spec = json.loads(Path('docs/validation/totum-source-row-protocol-v1.json').read_text())
folder = Path('outputs') / ('totum-source-fetch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
folder.mkdir(parents=True, exist_ok=False)
for key, source in spec['source_pins'].items():
    started = now()
    request = urllib.request.Request(source['requested_url'], headers={'User-Agent': 'Demeter-public-source-fetch/1'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data, status, kind = response.read(), response.status, response.headers.get('Content-Type')
        final = urlsplit(response.geturl())
    digest = hashlib.sha256(data).hexdigest()
    passed = status == 200 and len(data) == source['size_bytes'] and digest == source['sha256']
    with (folder / source['cache_filename']).open('xb') as target: target.write(data)
    receipt = dict(requested_url=source['requested_url'], resolved_url=urlunsplit(final._replace(query='', fragment='')),
                   final_url_query_omitted=bool(final.query or final.fragment), started_at_utc=started, completed_at_utc=now(),
                   http_status=status, content_type=kind, size_bytes=len(data), sha256=digest,
                   cache_filename=source['cache_filename'], frozen_pin_agreement=passed, distribution='fetch_only')
    with (folder / ('acquisition-' + key + '.json')).open('x', encoding='utf-8') as target: json.dump(receipt, target, indent=2)
    if not passed:
        raise SystemExit(f'Source drift: {key}. Candidate bytes and fresh receipt retained in {folder}; stop for source review.')
print(f'All byte pins match. Use --raw {folder} for the audit.')
"
```

Fresh receipts record redirected-query omission, including signed-download queries.
Historical receipts link/hash their ignored exact acquisition records; they are
not replaced. Live HTML or metadata may change: stop for source review on mismatch,
without automatic repinning. Fetching bytes performs no outcome analysis.

## Run the audit and understand its boundary

Run offline against the original pinned cache:

```text
uv run demeter evidence totum-source-rows --raw outputs/public-source-search-20260930 --output outputs/totum-source-rows.json
```

For fresh fetches, use the printed `--raw` path. Local byte verification does not
claim the new acquisition happened at historical receipt times. `--raw` is required;
the audit checks all five files before reading the selected cells. On October 1,
2026 UTC, a fresh execution matched the release metadata but stopped at changed
article HTML bytes (389952 bytes versus the frozen 389951). The remaining three
sources were not requested. A scoped comparison found identical approved methods
and access text; differing anchor IDs and other uninterpreted page bytes still
fail the original whole-document pin. Original matching snapshots are required
for this version; no repinning or fresh-download replay is claimed. Passing
software checks does not establish scientific release readiness.

The next decision is whether the source preserves enough observations for a
separately frozen analysis. Same-person pairing, unique record units, assay
validity, missing-code meanings and participant coverage must first be established.
Actual dates, diagnosis confirmation, treatment, death and loss processes are
still required by the [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md).
An available-pair description would not automatically be the randomized effect,
an annual progression/recovery rate, or an untreated-remission estimate.
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58) remain open. This audit activates
no parameter and identifies no UPF dose response, lag or national health effect.
