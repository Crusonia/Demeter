# Formulation and validation contracts

These are symbolic design contracts for selected mechanisms, not new executable
model semantics. There are no calibrated coefficients here. Use the current
[model specification](../MODEL_SPEC.md) for implemented health arithmetic.

## Formulation candidates

| ID | Required structure | Units, boundary, and linked design |
| --- | --- | --- |
| F-01 Stock and flow accounting | `d(stock)/dt = sum(inflows) - sum(outflows)`. Every transfer leaves one source and enters an identified destination; explicit loss/death flows have named sinks. | People, hectares, food units, tonnes C, or currency; flows in the corresponding unit/time. Stocks are not interchangeable. L-00/L-01/L-03/L-05/L-07/L-08/L-09/L-13/L-14. |
| F-02 Food and capacity balance | Inventory changes through deliveries minus fulfilled sales, processing use, and spoilage. Desired purchases are distinct from fulfilled purchases. Installed capacity changes through commissioned additions and retirement. | Consistent edible/as-purchased basis, conversion yields, products, and time units. Limit sales/throughput to available stock/capacity and account for every loss. I-02–I-05; L-03/L-04/L-06. |
| F-03 Decisions and perception | Desired adoption/investment/funding responds to information available to the actor; actual action is constrained by eligible stock, resources, and implementation delay. A perception state may use `d(perceived signal)/dt = (observed signal - perceived signal)/adjustment time` if supported. | Define the observable signal, expectation rule, saturation, lag, and alternative forms. No perfect foresight or profit maximization is assumed. No lag constant is supplied here. L-01/L-02/L-04/L-05/L-06/L-10/L-15. |
| F-04 Exposure and earlier-risk transitions | A defined food-basket change maps to intake/exposure, then to separately appraised transition hazards for an explicit eligible population. Competing transitions conserve people. | Food exposure units must match study definitions; hazards are per time, not probabilities. No automatic coefficient for a real-food/regenerative label and no automatic equivalence of PreChronic with IR. I-01/I-05/I-07; P-02/L-08/L-10/L-11/L-12. |
| F-05 Actor cash and payer economics | Cash changes through identified receipts minus payments, including explicit finance. `gross avoided treatment spending = reference eligible treatment spending - scenario eligible treatment spending`; `net payer benefit = gross avoided treatment spending - incremental intervention and administration outlays - additional outcome payments`, with mutually exclusive cost categories. | Currency/time or cumulative currency over a stated horizon/price year. Separate treatment from intervention spending so it is not subtracted twice; include membership and covered population changes. Distinguish resource costs, prices, cash flow, and accounting profit. I-08/I-09; P-01/P-02/L-05/L-07/L-08/L-09/L-12. |
| F-06 Value capture and budget response | Payments follow specified eligibility, attribution, and contract rules. A retained saving affects future funding only through an explicit actor rule. Without that rule, report the open pathway. | A producer's return depends on its received price, quantities, costs, and contracts; it is not the retail premium. Payer payment is food-provider revenue and payer expense, not another social benefit. P-01/P-02/L-02/L-08/L-10/L-12. |
| F-07 External effects | Track action -> physical load/state -> recipient exposure -> consequence, compared with the counterfactual. Add compensation and residual uncompensated effects as separate accounts. | Pollutant mass/time, carbon stock/flow, habitat measures, care time, or other explicitly defined units. Monetization is a separate evidence-dependent step. P-03/L-13/L-14 and the X- register. |
| F-08 Observation and aggregation | Map latent/model states into the actual measurement definitions, including timing, error, selection, and aggregation. Specify exchange quantities for any modules with different steps. | Do not fit a disease prevalence to a different diagnosis or compare food availability directly with individual intake. Preserve total quantities across time/space aggregation. All packages, especially I-11/I-12. |
| F-09 Spatial land and nutrient capacity | Exclusive physical land stocks change through named conversion/restoration flows; product output follows local use/yields; edible deliveries reconcile feed, processing, trade, losses and inventory before nutrient composition is applied. | Hectares and hectares/time; product mass/time; nutrient units/time on the matching edible basis. Co-use does not duplicate area; demand/intake and actor objectives remain separate. Q-05/RM-06, I-13, L-16/L-17/P-06/P-07; equations and future tests in the [land-use brief](07_LAND_USE_AND_NUTRITION_TRADES.md). |

F-05 is a payer perspective under a specified counterfactual. It is not an estimate
of total social welfare or net lifetime savings. A lower provider payment changes
both actors' finances but need not free an equivalent amount of real resources.
Do not add health value, avoided care costs, and payments into a single total
without a defensible valuation boundary that excludes overlap.

## Tests required for a selected mechanism

| ID | Test | Evidence it supplies / what would fail |
| --- | --- | --- |
| T-01 Units and conservation | Check dimensions and stock/flow identities at every step, including transfers, conversions, losses, deaths, and payments. | Detects people, food, cash, or physical loads created/disappearing without a named flow; does not validate a causal effect. |
| T-02 Initial and extreme conditions | Test zero eligible people, no intervention, exhausted inventory, no available cash, saturated capacity, and the supported extremes of each input. | No negative stocks or impossible participation; no benefit without the mechanism that produces it. Unknown evidence is not set to zero as an empirical estimate. |
| T-03 Step and horizon sensitivity | Reduce step sizes and change the evaluation horizon; check convergence and terminal treatment. | Finds numeric artifacts, incorrectly aggregated rates, and a business case driven by ignoring delayed costs. |
| T-04 Feedback isolation | Freeze or remove a selected feedback link while preserving stock/flow/accounting identities and exogenous paths. Compare the resulting trajectory with the complete candidate model. | For L-08, remove reinvestment while retaining the health pathway; savings alone must not fund more enrollment. Attribute behavioral changes to structure, not labels. |
| T-05 Alternative structures | Compare fixed versus responsive prices, alternative adoption rules, no causal dietary effect as an explicit null hypothesis, and separate versus competing budgets. | Tests whether a conclusion survives its premises. A favorable reinforcing loop is not guaranteed to dominate. |
| T-06 Behavior and holdouts | Compare trajectories to reference modes using calibration/holdout separation, measurement models, known breaks, and uncertainty. | A good fit alone is insufficient; avoid future data in earlier decisions, parameters, or expectations. |
| T-07 Capture and externality reconciliation | Reconcile counterpart payments and count each physical/health benefit once. Compare no-payment, specified-payment, and nondelivery cases. | A retail premium cannot appear fully at multiple stages; a savings payment cannot be both a transfer and additional system value. |
| T-08 Uncertainty and applicability | Propagate appraised uncertainty/dependence and structural alternatives; flag extrapolation and unresolved inputs. | No precise business or clinical conclusion when its material links remain synthetic/unresolved. |
| T-09 Land/capacity and demand trade | Reconcile land/co-use, product/feed/trade balances and regional concentration; compare productivity, demand and integration alternatives. | Equal acres need not imply equal nutrient capacity; spending is not quantity; national buffers cannot erase local effects; no automatic restoration or nutrient benefit. Detailed future tests in the [land-use brief](07_LAND_USE_AND_NUTRITION_TRADES.md). |

## Review packet before implementation

Choose a Q-/RM- question, the relevant L-/P- mechanisms, X- entries, and I-/F-/T-
contracts. Supply the equations and units, precise state/flow definitions,
evidence keys and source receipts, parameter uncertainty, initial conditions,
time-step rationale, measurement mapping, and the proposed failure tests. Review
the complete loop's applicability, not merely individual citations.

When coding is authorized by the active phase, add links back from the implemented
functions/tests to the selected design records in the PR documentation. Record
which loops are actually closed, which links remain exogenous, and what the tests
show. Update [MODEL_SPEC.md](../MODEL_SPEC.md) and evidence metadata when semantics
change. Until then, these documents are inputs to design and do not make the
broader model or its business conclusions operational.
