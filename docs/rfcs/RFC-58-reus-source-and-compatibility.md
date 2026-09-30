# RFC-58 extension: corrected Reus endpoint and model compatibility

Date: September 30, 2026. Status: used-source reproduction and synthetic
compatibility assessment; external expert review pending. Parent:
[RFC-58](RFC-58-food-pathway-identification.md). Current phase: v0.1 health.
Design links: I-01/I-05/I-07/I-11/I-12, P-02, F-04/F-08 and T-01/T-05/T-08.
Business externalities and value capture are inapplicable to this evidence check.

## What this advances

Implement source-grounded extraction of a specified dietary-regimen/first-diabetes
contrast, retaining its correction, uncertainty, alternatives and unresolved
mechanism mapping. Add executable counterexamples using the current health and
dietary-response operators. This addresses the source and equation/observation
parts of #58; it does not replace its full pathway-validation requirement.

The [frozen protocol](../validation/reus-diabetes-protocol-v1.json) precedes
executable effect-cell extraction and new synthetic witness calculations.
Published results and source structure were already inspected. This is neither
preregistration nor independent validation.

## Clinical source and estimand

Use the separate [Reus report](https://doi.org/10.2337/dc10-1288) and its
[2018 correction](https://doi.org/10.2337/dc18-er10). Extract all three overall
contrasts in each of correction Table 3's original and new multivariate rows.
Compare the old row to the original report's Table 2. Preserve any discrepancy.
Do not select by significance or pool the combined arm with its constituents.

The endpoint is first incident diabetes under assigned Mediterranean dietary
counseling plus offered virgin olive oil or nuts, versus control dietary advice,
in the selected older high-cardiovascular-risk Reus population without baseline
diabetes. It is not a measured UPF-dose contrast or a current-prediabetic-state
transition. The correction excludes nonrandomized household partners; original
and corrected analyses reuse participants and control comparisons.

Record reported Cox hazard ratios and confidence intervals as benchmark-only
estimated parameters. They are dimensionless, not annual hazards or cumulative
risk ratios. Joint covariance and the risk sets needed to reconstruct the
adjusted Cox fit are unavailable in these aggregates. Retain source intervals
without inventing a joint sampling distribution. Compare the ratio null to the
reported interval only; that is not a pass/fail test of Demeter's mechanism.

The multivariate model conditions on weight change during follow-up. Its total
causal interpretation needs assessment beyond randomized assignment. The
correction and original adjustment footnotes also differ on age/sex: preserve
that source issue. Annual diagnostic observations, confirmation, censoring,
missing tests and competing deaths need a compatible observation model before
clinical transition use. The unavailable multicenter Annals correction and
overlapping PREDIMED reports remain separate; neither is silently substituted.

## Executable model compatibility

Keep clinical estimates entirely separate from the synthetic witnesses. Use
existing synthetic registry hazards and composition with protocol-registered
software constants. Do not mutate active inputs or fit a clinical parameter.

For the isolated implemented annual survivor operator, conditional on incoming
IR survivors, the diabetes-entry probability is
`p_D(r,d) = d/(r+d) * [1-exp(-(r+d))]`. H-to-IR entrants cannot enter diabetes in
that same operator step. Different recovery/diabetes rates can yield identical
one-step diabetes entries but different H/IR endpoint stocks and later entries.
Changing only upstream progression also leaves that first endpoint unchanged.
The frozen analytic construction requires no root search or source fitting.

For the implemented legacy response, `L(t)=beta*delta*[1-exp(-t/tau)]`.
Inverse dose/coefficient rescaling preserves the trajectory; a distinct
lag/coefficient pair can preserve the first response but diverge later. Use the
existing `relax` helper to test this. These are software/mathematical witnesses,
not clinical effects or a claim about identifying the trial's Cox likelihood.

Test conservation, nonnegative/finite bounds, analytical/operator agreement,
matched first endpoints, different later endpoints, and explicit structural
nulls. Hash the invoked engine helpers and freeze reference definitions. Source
HRs must never enter the synthetic witness calculations. Preserve unknown dose,
lag and transition mapping as unresolved rather than assigning the same ratio
to multiple arrows.

## Validation and disposition

The extraction can reproduce reported cells and their original/corrected labels.
It cannot independently reproduce the fitted Cox analysis or validate a national
diet-to-health pathway. A qualifying clinical bridge still needs compatible
glycemic history, event ascertainment/timing, treatment and competing-event
information, measured intervention exposure and a justified observation mapping.
An independent evaluation must match the claimed population and endpoint.

Compare canonical baseline, UPF and PreChronic outputs before/after; document
added registry records and unchanged active equations/parameters. Audit rights,
source pins and distribution. Run targeted and full software checks. Full XML
articles stay fetch-only; distribute factual estimates, receipts and original
Demeter transforms. No individual records are requested or exported.

The work is Codex-assisted for the Food is Health-affiliated project. Automated
critique is not independent human review. No scientific release blocker is
removed; #58 remains open and external expert assessment remains pending.
