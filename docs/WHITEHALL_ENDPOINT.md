# Whitehall II: what can a follow-up count tell us?

This package reproduces two published FPG endpoint counts and evaluates a
**conditional binomial working model**. It also offers a descriptive-only mode.
The [design RFC](rfcs/RFC-57-58-whitehall-fpg-endpoint.md) explains the equations,
assumptions and remaining clinical requirements. This work fits an endpoint
probability under stated assumptions; it does not fit annual transitions or
activate a health-model parameter.

FPG means fasting plasma glucose. [Vistisen et al. (2019)](https://doi.org/10.1007/s00125-019-4895-0)
examined a selected British occupational cohort at phase 7 (2002–2004) and phase 9
(2007–2009), approximately five years later. We use only the supplement's Table 1,
**By FPG**, **N** column, for `Normoglycaemia` and `Prediabetes or diabetes`.
The normal label is an observation at re-examination, not sustained untreated
remission. The second label combines persistent prediabetes and diabetes.

| Selected source endpoint | Published N |
| --- | ---: |
| Normoglycaemia | 365 |
| Prediabetes or diabetes | 455 |
| Sum of the selected cells | 820 |

The main article's FPG paragraph gives the same denominator and normal count.
The observed normal-label fraction is 365/820 (about 44.5%) in this retained
source sample. The [aggregate report](validation/issue-57-58-whitehall-endpoint.json)
contains the working-mode interval and its assumptions; it is not an annual
recovery probability.

## Run it on Windows, macOS or Linux

Follow [Getting started](GETTING_STARTED.md) to install Git and uv and clone
Demeter. From its repository folder, run:

```text
uv sync --locked
```

If both pinned source PDFs are already in `outputs/public-source-search-20260930`,
skip the fetch block. Otherwise paste this entire block in Windows **PowerShell**
or macOS/Linux **Terminal**. It creates a new ignored folder and fresh acquisition
receipts. A mismatch stops the fetch; never replace the frozen hashes just to make
the command pass.

```text
uv run python -c "
import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
now = lambda: datetime.now(timezone.utc).isoformat()
spec = json.loads(Path('docs/validation/whitehall-fpg-endpoint-protocol-v1.json').read_text(encoding='utf-8'))
folder = Path('outputs') / ('whitehall-source-fetch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
folder.mkdir(parents=True, exist_ok=False)
for key, source in spec['source_documents']['required_source_receipts'].items():
    started = now()
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'Demeter-public-source-fetch/1'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data, status, kind = response.read(), response.status, response.headers.get('Content-Type')
        final = urlsplit(response.geturl())
    digest = hashlib.sha256(data).hexdigest()
    passed = status == 200 and len(data) == source['size_bytes'] and digest == source['sha256']
    with (folder / source['cache_filename']).open('xb') as target: target.write(data)
    receipt = dict(requested_url=source['url'], resolved_url=urlunsplit(final._replace(query='', fragment='')),
                   final_url_query_omitted=bool(final.query or final.fragment), started_at_utc=started, completed_at_utc=now(),
                   http_status=status, content_type=kind, size_bytes=len(data), sha256=digest,
                   cache_filename=source['cache_filename'], frozen_pin_agreement=passed, distribution='fetch_only')
    with (folder / ('acquisition-' + key + '.json')).open('x', encoding='utf-8') as target: json.dump(receipt, target, indent=2)
    if not passed:
        raise SystemExit(f'Source drift: {key}. Candidate bytes and fresh receipt retained in {folder}; stop for source review.')
print(f'All byte pins match. Use --raw {folder} for the endpoint analysis.')
"
```

Run offline against the original cache:

```text
uv run demeter evidence whitehall-endpoint --raw outputs/public-source-search-20260930 --output outputs/whitehall-endpoint.json
uv run demeter evidence whitehall-endpoint --raw outputs/public-source-search-20260930 --descriptive-only --output outputs/whitehall-descriptive.json
```

For a fresh fetch, replace the `--raw` path with the folder printed above. The
commands need no server, account or participant-data access. They verify both
PDFs and the frozen design/receipt/registry agreement before computing results.
An input failure saves a failed aggregate report and exits with code 1.
Outputs cannot replace the evidence registry, frozen records or source files.

## Read the result in two layers

The descriptive fraction is `normal_label_n / paired_n`. It describes the
retained, classifiable source sample. Descriptive-only mode leaves the sampling
interval unavailable; an interval needs assumptions about repeated sampling.

The default working mode treats labels as independent Bernoulli observations
with one common probability. It reports the fitted endpoint probability, its
normalized log likelihood at that probability, and a two-sided equal-tail
Clopper–Pearson interval at the declared confidence setting 0.95. That interval
is calculated here; it is **not a published Whitehall interval**. It has its
coverage interpretation within the assumed binomial experiment
([method reference](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/binom.test.html)).
The publication does not establish those iid/constant-probability assumptions.
The interval omits selection, clustering, measurement, treatment/history and
population-transport uncertainty. It is not a causal health finding.

The analysis design was [frozen](validation/whitehall-fpg-endpoint-protocol-v1.json)
before the planned selected-cell capture and calculation, after earlier search
snippets and an incidental abstract scan had exposed descriptive results.
This chronology prevents a preregistration or independent-validation claim.
Main-article denominator/numerator agreement is a same-source consistency check.

## Questions a new contributor should ask

- **Does a normal test mean the person became metabolically healthy?** No. It
  records the source FPG category at one examination. Prior diagnosis, treatment
  and sustained remission require additional evidence.
- **Can we divide the fraction by five to get an annual recovery rate?** No.
  Actual intervals and paths differ, and a terminal category can result from
  many progression/reversal histories. See the RFC's synthetic ambiguity example.
- **What happened to missing participants?** These cells do not tell us.
  Complete-case retention does not classify loss, death or unmeasured outcomes.
- **Can we combine the FPG, OGTT and HbA1c groups?** Their participants overlap;
  this package uses FPG alone and does not multiply independent likelihoods.
- **Does this show that changing food reduces healthcare costs?** No. The source
  supplies no causal dietary assignment or UPF dose/substitution/lag. Cost and
  value-chain mechanisms belong downstream of validated health relationships.
- **Why add this to a large model?** It makes one observation contract and its
  limitations executable. Demeter grows through inspectable increments, with
  unsupported parameters left unresolved rather than given convenient values.

## Source and redistribution record

Both complete publication PDFs remain **fetch-only** in ignored local storage.
The repository contains limited attributed aggregate reproduction, source pins,
[historical receipts](validation/whitehall-fpg-source-receipts-v1.json), equations
and transforms. The article's physical p5/printed 1389 grants CC BY 4.0; publication
rights do not grant access to Whitehall participant records. No application,
agreement, contact or participant download is part of this work.

| Required source | Public URL | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Main article PDF | [Publisher](https://link.springer.com/content/pdf/10.1007/s00125-019-4895-0.pdf) | 543921 | `e89dfe23cdb184e9f1fbb04f58678d23e97f2ea8ab5d215df8aa85716799d712` |
| ESM PDF | [Publisher supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs00125-019-4895-0/MediaObjects/125_2019_4895_MOESM1_ESM.pdf) | 294249 | `a78d0ead94ff6571518907beaa0805656902df4ec4ba30fc9c038889187bb894` |

Fresh receipts record actual new acquisition times; the runtime verifies local
bytes without claiming they were acquired at the historical times. A publisher
change requires review and a versioned contract, never silent repinning.
The exact fetch block was executed on Windows on October 1, 2026 UTC: both new
downloads matched the frozen size/hash pins. This verifies that snapshot's fetch
path, not permanent publisher availability or empirical-model adequacy.
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58) remain open. Clinical transitions,
competing mortality, diet response, U.S. transport and independent scientific
evaluation remain unresolved.
