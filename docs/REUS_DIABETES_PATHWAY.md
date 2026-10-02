# Reus diabetes benchmark: what it teaches us

Demeter can now reproduce six reported diabetes comparisons from the corrected
PREDIMED-Reus publication and run a separate synthetic model diagnostic. This is
**used-source reproduction, not independent validation**. The results remain
benchmark-only: they do not change a dietary coefficient, activate a clinical
transition, or establish a national health or healthcare-cost forecast.
[#58](https://github.com/Crusonia/Demeter/issues/58) remains open.

## What people were assigned

The [original Reus report](https://doi.org/10.2337/dc10-1288) studied older adults
in northeastern Spain who had high cardiovascular risk and no baseline diabetes.
They were not exclusively people with prediabetes. Participants received either
Mediterranean-diet counseling plus offered virgin olive oil, counseling plus
offered mixed nuts, or advice on a low-fat control diet. The offered amounts were
one liter of olive oil per week or 30 grams of nuts per day. Offered food is not a
measured consumed dose. The intervention did not prescribe energy restriction or
increased physical activity.

The [2018 Reus correction](https://doi.org/10.2337/dc18-er10) addresses household
members assigned to the same arm as a previously randomized relative. Its new
analysis excludes these nonrandomized partners. It does not replace the separate
multicenter diabetes correction, and a cardiovascular correction is not a
substitute for this diabetes source.

## How to read the numbers

A **hazard ratio (HR)** compares the modeled rate of first diabetes diagnosis
among people still at risk at each time, under the source's Cox analysis. A ratio
below 1 indicates a lower estimated hazard relative to the control group. It does
not give the probability that a person develops diabetes in the next year.

An annual risk is a probability over a specified year. A model transition hazard
is a rate for a specified starting state and destination, such as current
prediabetes to diabetes. Moving from a reported HR to either quantity requires
baseline rates, compatible starting states, observation timing and an appropriate
model. The Reus overall endpoint does not separate healthy-to-prediabetes from
prediabetes-to-diabetes effects. For example, the reported HR of 0.47 is neither a
47% annual probability nor a transition rate of 0.47 per year.

These are all six overall cells from **Table 3 of the 2018 correction**, including
its original and new multivariate-adjusted analyses. The three original tuples
also match the original report's Table 2. The intervals are reported 95%
confidence intervals, not prediction intervals or uncertainty about national
transport. Sources: [correction](https://doi.org/10.2337/dc18-er10) and
[original report](https://doi.org/10.2337/dc10-1288).

| Analysis | Assigned regimen versus control | HR | Reported 95% CI |
| --- | --- | ---: | --- |
| Original | Mediterranean diet + virgin olive oil | 0.49 | 0.25–0.97 |
| Original | Mediterranean diet + nuts | 0.48 | 0.24–0.96 |
| Original | Both Mediterranean arms combined | 0.48 | 0.27–0.86 |
| New, household partners excluded | Mediterranean diet + virgin olive oil | 0.47 | 0.23–0.97 |
| New, household partners excluded | Mediterranean diet + nuts | 0.47 | 0.23–0.98 |
| New, household partners excluded | Both Mediterranean arms combined | 0.47 | 0.26–0.87 |

The combined comparison reuses its constituent arms. All comparisons share
participants or controls, and the original and new analyses overlap. They are
not six independent studies. Demeter preserves the intervals without inventing
joint covariance, pooling these comparisons, or estimating an uncertainty
interval for the original-to-new difference. Whether an interval includes the
ratio null of 1 is a description of that interval, not a test that Demeter's
mechanism is correct.

## What is still unresolved

The [original methods and results](https://doi.org/10.2337/dc10-1288) describe
annual fasting-glucose or oral-glucose-tolerance testing, with confirmation
required. Follow-up ends at the last follow-up, death, or diagnosis; participants
without diabetes or lost to follow-up are censored at their last visit. Missing
tests and deaths matter. An observation model must distinguish a disease arising
between visits from its later detection; the source does not settle whether the
event date is the first positive test or confirmation. Its adjusted Cox HR is
not a competing-risk cumulative-incidence estimate.

The multivariate analysis adjusts for **weight change during follow-up**, which
occurs after assignment and could be part of the intervention's mechanism.
Randomized assignment alone therefore does not establish that this adjusted
coefficient is the total causal regimen effect. The original Table 2 footnote
lists age and sex; the correction's adjustment footnote omits them. Demeter
retains this discrepancy rather than silently deciding what was fitted.
[Original](https://doi.org/10.2337/dc10-1288);
[correction, Table 3 footnotes](https://doi.org/10.2337/dc18-er10).

The following mappings remain unresolved:

- **Dose:** counseling and offered foods do not identify a measured change in
  ultra-processed-food exposure, fiber, or a single ingredient.
- **Lag:** a follow-up contrast does not reveal when a clinical effect begins or
  how it changes after an intervention ends.
- **State:** a mixed population without diabetes is not the model's current
  prediabetic state, and no remission effect is identified here.
- **Transport:** the selected Reus cohort is not a national U.S. population.
- **Adjustment and observation:** post-assignment weight change, the footnote
  discrepancy, diagnosis dates, missed tests and competing events need explicit
  treatment before clinical use.

## What the synthetic diagnostic shows

The diagnostic uses registered **synthetic** hazards and dietary-response inputs.
No Reus HR is an input, and no clinical parameter is fitted. These calculations
are validation-only mathematical and software examples.

In Demeter's isolated annual survivor step, different recovery and diabetes
hazards can produce the same first-year diabetes entries while leaving different
healthy/prediabetic stocks and different second-year entries. Changing only
upstream progression also leaves that first-year endpoint unchanged, because new
prediabetic entrants cannot develop diabetes within that same operator step.

The dietary-response examples separately show that changing the dose and its
coefficient together can preserve a trajectory. A different lag/coefficient
pair can match the first response and diverge later. The diagnostic also checks
population conservation, nonnegative values, analytical arithmetic, identical
hazards and zero-response examples.

This explains why one observed endpoint needs a specified observation and
mechanism model. It is **not** a formal identification result for the trial's
multi-year adjusted Cox likelihood and does not prove a clinical effect is zero.
See the [design RFC](rfcs/RFC-58-reus-source-and-compatibility.md),
[frozen protocol](validation/reus-diabetes-protocol-v1.json), and
[dependency amendment](validation/reus-diabetes-amendment-1.json).

The original frozen results and dependency amendment remain unchanged. An
[additive numerical amendment](validation/reus-diabetes-amendment-2.json)
now pins the repaired annual competing-hazard helper after extreme finite
hazards exposed overflow/underflow failures. The
[separate replay](validation/reus-compatibility-numerics-v2-replay.json)
exactly reproduces every original synthetic witness result with unchanged
reference definitions, equations and tolerances. Only implementation/provenance
changes are declared; neither version fits or activates a clinical effect.

## Run the source reproduction

Start with [Getting started](GETTING_STARTED.md), then open a terminal in the
repository root and run `uv sync --locked`. The download step needs internet;
the evidence command reads local files and verifies their pinned SHA-256 hashes,
protocol and registered estimates before reporting success.

Full articles are **fetch-only** and stay in ignored `data/raw/clinical`. The
original has a CC BY-NC-ND 3.0 license; the correction states cited, educational,
not-for-profit, unaltered-use permission. Their full XML contents are not bundled
with the repository. Demeter distributes factual estimates, citations, receipts
and its own code. The download snippets below preserve existing files and use
exclusive creation for new files, so they never overwrite existing source bytes.

Windows PowerShell:

```powershell
uv sync --locked
@'
from pathlib import Path
from urllib.request import urlopen

folder = Path("data/raw/clinical")
folder.mkdir(parents=True, exist_ok=True)
for name, pmcid in [("reus-original.xml", "PMC3005482"), ("reus-correction.xml", "PMC6150430")]:
    path = folder / name
    if path.exists():
        print("Keeping existing source:", path)
        continue
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    with urlopen(url, timeout=60) as response:
        content = response.read()
    with path.open("xb") as source:
        source.write(content)
    print("Saved:", path)
'@ | uv run python -X utf8 -
uv run demeter evidence reus-diabetes --original data/raw/clinical/reus-original.xml --correction data/raw/clinical/reus-correction.xml --output outputs/reus-diabetes.json
Get-Content outputs/reus-diabetes.json
```

macOS or Linux:

```bash
uv sync --locked
uv run python -X utf8 - <<'PY'
from pathlib import Path
from urllib.request import urlopen

folder = Path("data/raw/clinical")
folder.mkdir(parents=True, exist_ok=True)
for name, pmcid in [("reus-original.xml", "PMC3005482"), ("reus-correction.xml", "PMC6150430")]:
    path = folder / name
    if path.exists():
        print("Keeping existing source:", path)
        continue
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    with urlopen(url, timeout=60) as response:
        content = response.read()
    with path.open("xb") as source:
        source.write(content)
    print("Saved:", path)
PY
uv run demeter evidence reus-diabetes \
  --original data/raw/clinical/reus-original.xml \
  --correction data/raw/clinical/reus-correction.xml \
  --output outputs/reus-diabetes.json
cat outputs/reus-diabetes.json
```

Inspect `source_reproduction_passed` and the nested
`compatibility_diagnostic.results.software_witnesses_passed`. Both must be true
for this command to exit successfully. `scientific_release_ready` remains false.
Success establishes source-cell reproduction and synthetic software checks,
not independent clinical validation. The command does not refit the Cox model,
download sources implicitly or export participant records.

A checksum error means the local bytes differ from the frozen source. Preserve
the file and investigate its provenance; do not overwrite it or change a pin to
force a pass. The expected hashes are recorded in the
[protocol's source pins](validation/reus-diabetes-protocol-v1.json).

## Run the diagnostic without clinical downloads

Once the environment is installed, this command works on Windows, macOS and
Linux without article downloads or network access:

```text
uv run --offline demeter evidence pathway-compatibility --output outputs/pathway-compatibility.json
```

It checks the frozen synthetic definitions and engine-helper hashes, then writes
the witnesses and their checks. Inspect `results.software_witnesses_passed`.
This is a software validation result; clinical effect readiness remains false.

## The next evidence deliverable

Use the [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md) before attempting a clinical fit. For
each proposed source, record baseline glycemic states and thresholds, repeated
tests and confirmation, visit intervals, first-event dating, assigned treatment
and measured exposure, missing observations, and death/loss handling. Map those
observations to the model's states and flows, and state which parameters the
available information can support. Unsupported mappings remain unresolved.

The [original Diabetes Prevention Program report](https://doi.org/10.1056/NEJMoa012512)
is a bounded next appraisal candidate, with a
[public primary report](https://pmc.ncbi.nlm.nih.gov/articles/PMC1370926/).
Review its primary methods, protocol, actual public evidence availability and
rights against that contract before extracting new effects. A lifestyle package
does not by itself isolate a dietary or UPF effect. Neither candidate status nor
its separate trial origin establishes compatible independent validation.

External expert review, food-to-disease identification, uncertainty and v0.1
scientific acceptance remain pending. Automated Codex critique is not independent
human scientific approval.
