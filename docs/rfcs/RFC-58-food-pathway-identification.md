# RFC-58: Separate a randomized food contrast from the disease bridge

Status: source appraisal and proposed analysis boundary; no engine activation.
Supports #58, I-07 and the health portion of P-02. September 29, 2026 (UTC).

## A precise first contrast

Use a specified offered menu and eating environment, rather than the label
“real food,” as the intervention. A reproducible upstream candidate is the
randomized inpatient menu contrast in
[Hall et al. (2019)](https://pubmed.ncbi.nlm.nih.gov/31105044/),
doi:10.1016/j.cmet.2019.05.008. Its short-term intake endpoint is relevant to food
exposure, but does not identify the engine's progression, reversal or mortality.

| Design element | Proposed supported scope |
| --- | --- |
| Intervention and comparison | The trial's ultra-processed versus unprocessed offered menus, under the recorded ad libitum inpatient protocol |
| Population and timing | The enrolled adult volunteers and the protocol's diet periods; no national or lifetime transport |
| Endpoint | Participant-period mean daily energy intake, in kcal/day, with the paired diet contrast |
| Causal interpretation | A randomized contrast between complete menu regimens in this setting; not the isolated effect of processing, an ingredient, or every product sharing a label |
| Unit of analysis | Participant, retaining paired periods and daily observations as repeated measurements |
| Engine applicability | Upstream evidence candidate only; no conversion to a relative UPF multiplier or disease hazard |

The [author's OSF project](https://osf.io/rx6vm/) links the
[clinical protocol](https://osf.io/3bjxv/) and
[data and SAS code](https://osf.io/khqug/). The public API and downloads were
accessible during this appraisal, even though the browser rendering of OSF failed.
The intake archive contains daily intake, baseline, weight and other endpoint
files. Headers and missingness were inspected; no new estimate has been fitted.
The author code calculates participant-period mean intake before the paired
comparison. Its archive also documents a later body-composition timing adjustment.

The [published correction](https://pubmed.ncbi.nlm.nih.gov/31269427/),
doi:10.1016/j.cmet.2019.05.020, must remain attached to the source. Do not substitute
the earlier preprint for the corrected publication. Before reproduction, verify
diet order and corrections against the selected endpoint and pin the actual
download version. The inspected OSF node metadata did not declare a license;
downloadability alone does not authorize redistributing its participant files.
The research copies remain in ignored storage. No raw archive is committed here.

## A newer study tests a different contrast

[Dicken et al. (2025)](https://www.nature.com/articles/s41591-025-03842-0.pdf),
doi:10.1038/s41591-025-03842-0, compares offered UPF and minimally processed diets
that both follow UK dietary guidance. Its primary endpoint is percentage weight
change in a community crossover trial. It is not a direct replication of the
inpatient energy-intake estimand. The paper reports sequence-related differences,
missing-data sensitivity analyses and limits on carryover assessment. The
supplement's energy-density correction must be checked before using menu values.

The paper's data-availability statement requires author approval and offers
summary, rather than individual-level, data. Its
[analysis code is public](https://github.com/SamuelJDicken/UPDATE).
No data request or message has been sent. A comparison with this study must retain
its different regimen, population, setting, endpoint and duration. Do not pool
the two studies as interchangeable dose-response observations.

## What must be registered before reproduction

- Exact source receipts, corrections and redistribution disposition. Separate
  immutable downloads, transforms and permitted aggregate outputs.
- The diet labels, participant-period completeness rules, endpoint aggregation,
  paired estimand, interval method, missingness handling and order/period
  sensitivity analysis. Preserve the null and uncertainty rather than treating
  significance as a clinical pass.
- All analysis constants and substantive quantities in the evidence registry.
  This design RFC introduces no active numeric parameter. A later extraction
  must register units, status, population, timing and applicability explicitly.
- Comparison with the corrected published result. This is reproduction on used
  data, not independent validation. A separate evaluation must match any broader
  predictive claim.

## The unfilled link to the health engine

The engine currently maps a relative dietary exposure to multiple metabolic
transition hazards using synthetic coefficients and delays. The offered-menu
trial does not identify that map. In particular:

1. A whole-regimen intake contrast does not provide a continuous effect per unit
   of UPF energy share, food weight or servings. These units cannot be substituted.
2. Intake is not weight change, and neither is a diabetes transition hazard.
   Energy balance, changing expenditure, response timing and exposure persistence
   would require a separately validated bridge if that mechanism were selected.
3. The disease endpoint must match one specific transition and observation model.
   An incident-T2D ratio cannot be applied to both upstream progression arrows.
4. Follow-up and treatment histories must identify delay and reversibility.
   Long-run retention, age transport and national effects remain unresolved.

An alternative is to select a directly measured incident-disease endpoint, but
the current observational UPF appraisal has incompatible exposure units and
unresolved confounding; see [clinical evidence](../CLINICAL_EVIDENCE.md). The model
must distinguish that associational option from a randomized regimen contrast.

## Current disposition

This RFC selects an auditable upstream candidate and explains why it cannot yet
replace the health coefficient. No disease bridge, new model state, clinical
grade, effect estimate or economic conclusion is activated. Next: verify rights
and corrected source identity, register and reproduce the narrow endpoint, then
choose and validate a compatible disease bridge or explicitly narrow the model's
claim. #58 and scientific v0.1 remain open.
