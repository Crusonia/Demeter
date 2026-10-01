# Following remission across visits without inventing relapse

Demeter can now preserve information about the same people's source-defined
remission labels across two visits. It calculates the range of paired tables
compatible with the available counts, and keeps missing assessments and possible
deaths separate from assessed nonremission. It does not fit annual clinical rates
or change the health engine. This advances the temporal observation work in
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58); both remain open.

After [installation](GETTING_STARTED.md), Windows PowerShell, macOS and Linux use
the same command, with the three matching source files in an ignored directory:

```text
uv run demeter evidence paired-remission --raw outputs/direct-sources --output outputs/paired-remission.json
```

No server is needed. A source mismatch saves a sanitized failure report and exits
with status 1. Successful source checks concern the amended source selection;
they do not turn the original failed intake into a passing check.

## What the paired information adds

The overlapping [one-year accepted DiRECT report](https://eprints.gla.ac.uk/153078/13/153078.pdf),
[two-year accepted report](https://eprints.gla.ac.uk/180894/13/180894.pdf), and
[published abstract at NLM](https://pubmed.ncbi.nlm.nih.gov/30852132/) describe
selected UK primary-care participants with diagnosed T2D. Their intervention
combines diet replacement, food reintroduction, support and medication changes.
It is not an isolated processing or UPF-dose experiment.

The published abstract states 149 intervention ITT participants and separately
reports 53 second-visit remission participants. The first report gives 68
first-visit positives. Conditional on those counts referring to the same stated
ITT cohort, their marginals alone allow between zero and 53 people to be positive
at both visits. An endpoint total cannot identify which people changed.

The two-year post-hoc weight analysis reports a maintaining-remission subgroup
of 48. Conditional on its same-cohort membership and stated paired-positive
meaning, it supplies a lower bound. Its completeness as the whole paired cell
is not certified; the software retains both interpretations:

| Quantity among the 68 first-visit source positives | Marginals only | With the conditional positive-subgroup constraint |
| --- | ---: | ---: |
| Positive at both source visits | 0–53 | 48–53 |
| Primary outcome failure at the second visit | 15–68 | 15–20 |
| Assessed nonremission, considered separately | 0–68 | 0–20 |
| Unassessed/unknown criterion, considered separately | 0–68 | 0–20 |
| Death, considered separately | 0–68 | 0–20 |

These are deterministic bounds over compatible source-label tables, **not
confidence intervals**. The last three components must partition the failures;
their upper bounds cannot all be selected at once. Death and unassessed outcome
are mutually exclusive within a completion, while their actual allocation is
unknown. A lower bound of zero does not mean zero observed deaths or relapses.
Sampling, practice clustering, measurement error and national transport remain
outside these ranges. Without trusting the source's positive classifications,
the ranges do not bound true latent physiological states.

The saved [aggregate report](validation/issue-57-58-paired-remission.json) includes
whole extreme tables that conserve the cohort, coupled cell ranges, conditional
shares, assumptions and immutable source/code hashes. The standalone Python
function [paired_remission_bounds](../src/demeter/analysis/paired_remission.py)
accepts supplied integer counts; it does not infer diagnosis history from them.
The DiRECT source wrapper retains the trial's diagnosed-T2D history explicitly.

## A source conflict remains visible

The accepted two-year PDF actually prints `53/129` in the selected remission
sentence, while both reports define the ITT population as 149 per group. The
[original intake failed](validation/direct-paired-failed-intake-v1.json) and stays
unchanged. The published abstract supplies separate cohort and remission counts;
it does **not** print a remission denominator. The amended analysis prefers those
published counts under the explicit common-ITT scope, corroborated by the
abstract's ITT methods. It does not repair the PDF or infer a count from a rounded
percentage. No author-issued erratum or corrected version-of-record fraction was
verified. The failed XML locator selection is also retained.

The [RFC](rfcs/RFC-57-58-paired-remission-observations.md),
[original protocol](validation/direct-paired-observations-protocol-v1.json) and
[current source amendment](validation/direct-paired-observations-amendment-v3.json)
record the sequence. Each selection was committed before its planned count
capture, after earlier source exposure. This is used-source work, not
preregistration, independent validation, or a new independent trial.

## Why this does not establish a remission rate

The primary outcome counts unavailable assessments as failure and permits
GP-record substitutions. Available weight data does not establish a complete
glycemic/medication assessment. A second-visit failure therefore cannot be
automatically called measured clinical relapse. Remission at two nominal visits
does not establish uninterrupted medication-free remission between them.
Actual observation windows, medication histories, competing death and selection
still need a compatible longitudinal package before fitting clinical hazards.

Prior diabetes remains part of the history. A low measured glucose or remission
label does not make someone never-diabetic healthy, and this analysis activates
no T2D-to-healthy transition, national rate, dietary coefficient or lifespan effect.
The [before/after record](validation/issue-57-58-paired-remission-before-after.json)
verifies unchanged canonical numerical scenarios and prior active parameters.
The scientific release check still fails on the wider unresolved clinical inputs.

For a first learning exercise, compare the two paired ranges above. Then consider
which extra observation would narrow the uncertainty: a same-person glycemic
assessment, a medication-free history, a missed-visit reason, or a death record.
Another marginal percentage cannot provide that linkage. The range shrinks when
information is added; health has not improved because classification improved.

## Obtain and verify the source files

The [frozen receipt inventory](validation/direct-paired-source-receipts-v1.json)
and v3 amendment identify the exact filenames, URLs and SHA-256 values. Keep full
publications/XML outside Git. Downloadability does not grant controlled participant
data or redistribution rights; only limited attributed aggregate facts and Demeter
transforms are committed here.

The following Python block works on all three operating systems. Save it as
`outputs/fetch_direct_sources.py` and run `uv run python outputs/fetch_direct_sources.py`.
It creates a fresh directory, preserves actual acquisition times, stops on any
source drift, and never replaces an existing source:

```python
import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

protocol = json.loads(Path("docs/validation/direct-paired-observations-protocol-v1.json").read_bytes())
amendment = json.loads(Path("docs/validation/direct-paired-observations-amendment-v3.json").read_bytes())
pins = {**protocol["source_receipts"], "published_abstract": amendment["published_source"]}
folder = Path("outputs") / ("direct-fetch-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
folder.mkdir(exist_ok=False)
for label, pin in pins.items():
    started = datetime.now(timezone.utc).isoformat()
    with urllib.request.urlopen(pin["url"], timeout=30) as response:
        content, final_url = response.read(), response.geturl()
    finished = datetime.now(timezone.utc).isoformat()
    target = folder / pin["cache_filename"]
    with target.open("xb") as file:
        file.write(content)
    sha = hashlib.sha256(content).hexdigest()
    receipt = {"url": pin["url"], "final_url": final_url, "retrieval_started_utc": started,
               "retrieved_utc": finished, "size_bytes": len(content), "sha256": sha}
    (folder / (label + ".receipt.json")).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if sha != pin["sha256"] or len(content) != pin["size_bytes"]:
        raise SystemExit("Source changed; retain receipt and stop for a reviewed version update")
print(folder)
```

Use the printed folder for `--raw`. A current NLM XML response can change even
when the selected article facts are unchanged; that still fails the byte pin.
Preserve the failed fetch and review the source version rather than silently
replacing the receipt. Historical retrieval timestamps refer to the original
snapshots, not to a later local verification or fresh download.

Author/date: Codex-assisted work for the Food is Health-affiliated project,
October 1, 2026 UTC. Source/math assessment is scoped to these conditional
observation constraints; independent human scientific review remains pending.
