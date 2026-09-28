# Causal-loop register

These are candidate feedback explanations of the [reference modes](01_PROBLEM_BOUNDARY.md).
All loops except L-00 are **premises, not implemented or empirically established
Demeter loops**. Their signs are conditional hypotheses, not estimates of effect
size. Each arrow needs its own appraisal before implementation; methodological
references in the [design index](README.md) do not substantiate these food/health links.

## Reading the register

`A +(->) B` means increasing A increases B relative to what B otherwise would have
been, holding other causes fixed. `-(->)` means the opposite. `R` is reinforcing
(an even number of negative links); `B` is balancing (an odd number). Reinforcing
does not mean beneficial, and balancing does not mean harmful. Neither sign nor
loop count establishes which loop dominates behavior.

Every path returns to its starting variable. Stocks and material delays are named
separately so a chain of associations cannot be mistaken for a dynamic model.
Link polarity can change with regime, thresholds, or actor: narrow the domain or
split the formulation rather than assign a universal sign. A loop can be dormant
when a contract, capacity, or causal link is absent.

In the compact paths below, `+>` and `->` denote positive and negative links,
respectively. They are sign notation, not arithmetic or executable syntax.

## Closed feedback hypotheses

| ID / type | Signed closed path | Stock and delay to represent | Scope/status |
| --- | --- | --- | --- |
| L-00 / B: transition depletion | IR stock +> IR-to-T2D transition flow -> IR stock | People in IR; annual competing-hazard transitions. Flow is limited to survivors at risk. | Implemented bookkeeping in the current health engine; hazards and state allocation remain synthetic. See [model specification](../MODEL_SPEC.md). |
| L-01 / R: production learning | Practice area +> experience accumulation +> accumulated experience -> unit production cost -> expected margin +> conversion rate +> practice area | Area using a specified practice; accumulated operating experience. Learning and conversion delays. | Premise; agriculture/adoption, Phases 2–3. |
| L-02 / R: verification and trust | Verified-product sales +> verification funding +> verification coverage +> buyer trust +> repeat demand +> verified-product sales | Trust/perceived credibility with a defined measure; verification capability. Audit and belief-update delays. | Premise; food-system/behavior, Phases 2–3. |
| L-03 / B: inventory scarcity | Desired purchases +> fulfilled sales -> sellable inventory -> retail price -> desired purchases | Product inventory; order, delivery, and price-adjustment delays. Sales saturate at availability. | Premise; local price-responsive regime with nonzero inventory, Phases 2–3. |
| L-04 / B: supply response | Product price +> expected margin +> capacity investment +> installed capacity +> supply -> product price | Capacity and projects under construction; financing, build, and commissioning delays. | Premise; product/market boundary must be fixed, Phases 2–3. |
| L-05 / B: transition cash constraint | Conversion starts +> transition outlays -> liquid cash +> financeable conversion starts +> conversion starts | Producer cash and area in transition; outlay, credit, and receipt timing. | Premise; finance/agriculture, Phases 2–3. |
| L-06 / R: access and repeat demand | Repeat demand +> shelf-space allocation +> local availability +> adoption rate +> regular buyers +> repeat demand | Regular buyers and retailer assortment commitments; procurement and habit formation. | Premise; household/retail behavior, Phase 3. |
| L-07 / B: household budget constraint | Target-basket purchasing rate +> food expenditure rate -> unspent food budget +> affordable purchasing rate +> target-basket purchasing rate | Unspent budget during a stated budget period; income replenishment and purchase timing. | Premise; household budget accounting, Phase 3. |
| L-08 / R: prevention reinvestment | Supported participants +> sustained target-basket intake -> progression hazard +> disease incidence +> diagnosed disease stock +> covered treatment spending -> retained savings +> prevention funding +> enrollment +> supported participants | Participants, disease stocks, and prevention budget; engagement, disease, claims, and contract delays. | Premise; later health/Phase 4 linkage. Reinvestment requires an explicit funding rule and an evidenced dietary effect. |
| L-09 / B: delivery budget limit | Supported participants +> delivery spending -> available prevention budget +> enrollment +> supported participants | Participants and available budget; enrollment, attrition, and funding cycles. | Premise; prevention delivery/payment, Phase 4. |
| L-10 / B: response to disease burden | Diagnosed disease stock +> perceived disease burden +> prevention funding +> enrollment +> supported participants -> progression hazard +> disease incidence +> diagnosed disease stock | Perceived burden, enrolled people, and disease stocks; measurement, policy, and biological delays. | Premise; payer/public decision rule, Phase 4. |
| L-11 / R: illness and affordability trap | Chronic disease burden +> work limitations -> household income +> affordable target-basket quantity +> sustained target-basket intake -> disease incidence +> chronic disease burden | Disease stocks; accumulated household financial resources if needed. Earnings and biological delays. | Premise; only applicable employed-household contexts, Phases 3–4. |
| L-12 / R: treatment crowds out prevention | Treatment spending -> remaining prevention budget +> enrollment +> supported participants -> progression hazard +> disease incidence +> diagnosed disease stock +> treatment spending | Budget, participants, and disease stocks; appropriations and disease delays. | Premise; only with a constrained shared budget, Phase 4. |
| L-13 / R: soil and reinvestment | Specified-practice area +> soil carbon per hectare +> crop yield under specified conditions +> expected margin +> conversion rate +> specified-practice area | Practice area and carbon mass by matching spatial unit; derive carbon per hectare. Soil response, seasons, and investment delays. | Premise; all biological/economic links require local appraisal, Phase 2+. Soil carbon is not a universal soil-health score. |
| L-14 / B: pollution response | Nutrient-loss flow +> downstream pollutant stock +> perceived damage +> mitigation effort -> nutrient-loss flow | Pollutant stock and perceived damage; transport, monitoring, and response delays. | Premise; selected environmental/policy interface, Phases 2/4+. |
| L-15 / R: shared learning | Verified trial observations +> reusable public knowledge +> adoption rate +> participating farms +> verified trial observations | Participating farms and a defined stock of usable knowledge; trial, publication, and adoption delays. | Premise; explicit knowledge-sharing arrangement, Phases 2–3. |

## Evidence gaps and discriminating tests

No magnitude or lag is assigned below. A listed observation is a requirement to
investigate, not a claim that a dataset has already been acquired.

| Loop | Critical premise / required observation | Competing case or falsification experiment |
| --- | --- | --- |
| L-00 | Stock/flow identity is explicit; clinical hazard applicability remains unresolved. | Zero hazard gives zero flow; competing exits never overdraw the stock. Existing tests cover the mechanics. |
| L-01 | Comparable operating histories identify learning separately from selection, scale, and subsidies. | Freeze learning or allow persistent transition costs; adoption need not become profitable. |
| L-02 | Credible verification affects repeat purchases; sales fund verification under an actual rule. | Hold trust unchanged, test adverse audit results, or sever reinvestment; a badge need not create demand. |
| L-03 | Inventory conditions affect price and substitution in this channel. | Fixed prices or rationing replace price adjustment; zero inventory caps fulfilled purchases. |
| L-04 | Expected margins influence funded additions; extra supply affects price. | External price-taking, long build delays, finance constraints, or falling demand can prevent the balancing response. |
| L-05 | Transition outlays precede receipts and cash/credit constrain conversion. | External finance relaxes the constraint; stopping conversion must stop its incremental outlays. |
| L-06 | Shelf space improves actual access and repeat use for the specified population. | Fixed availability, high prices, attrition, or substitution can stall adoption despite shelf space. |
| L-07 | Budget identity, food prices, and purchase timing are measured consistently. | No negative cash without modeled borrowing; alternate income/budget constraints change the response. |
| L-08 | Defined earlier-risk cohort, causal dose/endpoint, net costs, payer retention, and reinvestment terms all support the chain. | Set the dietary effect to the null in a labeled structural alternative, remove savings retention, or remove reinvestment: the full feedback must break. |
| L-09 | Delivery costs and funding dates constrain reachable participation. | Costs can exhaust funding before health benefits arrive; budget injections must have an identified payer. |
| L-10 | Observed burden changes funding decisions, which reach the intended population. | Hold funding policy fixed; awareness alone must not alter disease dynamics. |
| L-11 | Illness affects disposable resources and diet in the selected households, after confounders. | Pension/benefit income or other causes dominate; no universal income or dietary response should be forced. |
| L-12 | Treatment and prevention compete for the same funding pool. | Separate budgets or committed prevention finance remove this crowd-out loop. |
| L-13 | Specified practice changes measured carbon, carbon contributes to yield in the studied setting, and margin drives adoption. | No yield gain, input tradeoffs, declining premium, or carbon loss can weaken/reverse the proposed links. |
| L-14 | Downstream damage is perceived and triggers effective mitigation. | No monitoring, enforcement, or effective response leaves an open damage pathway rather than this balancing loop. |
| L-15 | Others can access and use findings, including null/negative results, and adoption yields further comparable trials. | Private/unused knowledge, unrepresentative trials, or no learning benefit opens or reverses the proposed pathway. |

## Important open pathways

Do not label an economically interesting chain a feedback loop until its return
link and accumulation are specified. Arrows in this table show sequence only;
the signed notation above applies to the closed-loop table.

| ID | Open pathway to preserve | What closes it, if evidence supports closure? |
| --- | --- | --- |
| P-01 | Regenerative practice → measured attribute/cost → retail response → incremental retail margin → contractual producer share. | Producer returns change future conversion/investment; pair with L-01/L-04/L-05. A premium cannot simply be assumed. |
| P-02 | Earlier-risk intervention → sustained exposure → disease progression → utilization → payer net spending. | A funding or behavior response returns to enrollment/intake, as hypothesized in L-08/L-10/L-12. Current health results contain no payer-cost link. |
| P-03 | Practice/production → nutrient loss, emissions, or habitat effect → consequences for nonparticipants. | Monitoring, payments, liability, or policy changes behavior, as in L-14. Otherwise report the spillover without inventing a response. |

Before coding, expand each selected arrow into a link record containing its loop
ID and source/target names, causal claim, sign domain, equation/units, stock or
flow role, delay, evidence keys, applicability limits, and test. Trace the signs
of the actual equations and compare with the register. A diagram annotation
cannot override an equation or promote a premise to causal evidence.
