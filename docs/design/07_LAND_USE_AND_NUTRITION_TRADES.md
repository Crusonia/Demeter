# Land use, production capacity, and nutrition trades

Status: **future design premises**, assessed against public sources on 2026-10-01.
This brief feeds the [design registers](README.md); it adds no engine, fitted
coefficient, land-use forecast, investment conclusion or optimization result.
The v0.1 health acceptance gate remains unchanged.

## Decision to explain

Q-05 / RM-06: Under what conditions do solar, wind, data centers and urban
development materially change delivered food and nutrient capacity, and who gains
or loses as production and demand adjust? Compare regional outcomes with national
totals over time. A small national acreage share can coexist with substantial
local loss of a crop, water access, farm income or a viable farming network.

Test the opposing premise too: productivity growth, lower food losses, changes
in demand and co-use may offset some capacity loss. None guarantees preservation
of the same foods, nutrients, locations or beneficiaries. Separate physical
capacity, price/access and landowner livelihood, identity and succession decisions.

## Acreage claims and source definitions

The initiating estimates of **600,000 energy acres**, **60,000 data-center acres**
and **600 million production-farmland acres** are unverified proposals. They have
no supplied common year, footprint definition, geography or uncertainty. Do not
divide them into a model coefficient or treat the result as a food-security finding.

The figures below are source-appraisal context, **not admitted model inputs**.
Before numerical use, acquire versioned source receipts, definitions, transforms,
uncertainty and evidence-registry keys; retain unresolved coverage explicitly.

| Candidate source | Quantity actually reported | Interpretation limit |
| --- | --- | --- |
| [USDA NASS, February 2026, pp. 4, 13–14](https://www.nass.usda.gov/Publications/Todays_Reports/reports/fnlo0226.pdf) | U.S. land in farms: 873.95 million acres in 2025. | Includes grazing/pasture, woodland, uncultivated and conservation land. The 2025 estimate changed to a modeling approach after the June Area survey was not conducted. A stock decline does not identify physical development conversion. |
| [USDA ERS, August 2026 update](https://www.ers.usda.gov/topics/farm-economy/land-use-land-value-tenure/major-land-uses) | U.S. total cropland: 377 million acres in 2022. | Includes crops, idle cropland and cropland pasture; neither all farmland nor land producing food for direct human consumption. Use the [tables and documentation](https://www.ers.usda.gov/data-products/major-land-uses), with their revisions. |
| [USDA ERS ERR-330, May 2024 summary](https://www.ers.usda.gov/sites/default/files/_laserfiche/publications/109209/ERR-330.pdf?v=13751) | Estimated 2020 rural CONUS utility-scale direct footprints: solar 336,000 acres; wind 88,000 acres. | Excludes transmission infrastructure. Dated stocks within the study boundary, not full energy-system area, current national totals, annual conversion flows or acres all formerly farmed. |
| [DOE data-center FAQ, May 2026](https://www.energy.gov/indianenergy/articles/data-centers-tribal-economic-development-frequently-asked-questions) | Distinguishes facilities/campuses from additional electricity-generation land. | No comparable national data-center acreage total was verified for this brief. Keep it unresolved; avoid counting generation land both here and under energy projects. |

Wind project/lease boundaries differ from direct permanent/temporary disturbance
([NREL, 2009, sections 3.1–3.2](https://www.nrel.gov/docs/fy09osti/45834.pdf)).
USDA finds nearby agricultural retention and differing regional siting patterns
([USDA, September 2024](https://www.ers.usda.gov/amber-waves/2024/september/agricultural-land-near-solar-and-wind-projects-usually-remained-in-agriculture-after-development)).
Nearby retention does not prove crop production beneath solar arrays; crop,
grazing and habitat co-use need distinct measurements
([DOE agrivoltaics](https://www.energy.gov/cmei/systems/agrivoltaics-solar-and-agriculture-co-location)).

Candidate conversion sources include [NRCS NRI](https://www.nrcs.usda.gov/nri)
(non-Federal land, excluding Alaska),
[USGS Annual NLCD v1.2](https://www.usgs.gov/data/annual-national-land-cover-database-nlcd-collection-1-products-ver-12-june-2026)
(CONUS land cover, impervious surface and confidence), and
[USGS solar-array boundaries](https://energy.usgs.gov/uspvdb/data/).
Crosswalk boundaries and classification uncertainty. Changes in
[Census urban definitions](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/urban-rural.html)
are not physical conversion. A national acreage total cannot supply an unobserved
county distribution or land-quality weighting.

## Inputs that can change the result

| Layer and design inputs | Required distinction | Evidence or unresolved link |
| --- | --- | --- |
| Land/water: I-02/I-10/I-13 | Exclusive physical stocks; temporary disturbance, durable conversion and restoration; co-use; soil/land quality, water rights and seasonal supply. | Spatial histories, former use and retained output. A leased acre is not automatically a lost producing acre. |
| Production: I-02/I-03 | Row crops, fresh produce and livestock; harvest, feed, processing yields, edible output, losses, inventories, enterprise mix and inputs. | Local product-specific series; feed cannot also count as food delivered to people. Productivity gains and their lags remain to be appraised. |
| Productivity: I-02/I-11 | Physical yield, aggregate input productivity, prices and nutrient delivery. | [USDA TFP methods](https://www.ers.usda.gov/data-products/agricultural-productivity-in-the-united-states/methods) use market-weighted output relative to aggregate inputs and omit output-quality changes. TFP growth does not identify nutrient adequacy. |
| Nutrition: I-03/I-05/I-07 | Energy, protein, fiber, micronutrients and relevant limiting components; adequacy, affordability and actual intake by population. | [FoodData Central](https://fdc.nal.usda.gov/data-documentation/) distinguishes analytical, survey and label evidence. Nutrients per calorie, portion, dollar and hectare answer different questions; a universal score needs definition and validation. |
| Demand: I-05/I-07 | GLP-1 eligibility, access, dose, indication, adherence, duration and discontinuation; purchases versus intake; substitution and households. | [Semaglutide trial](https://pubmed.ncbi.nlm.nih.gov/33269530/) measures meal-intake effects in its studied population. [The No-Hunger Games](https://journals.sagepub.com/doi/10.1177/00222437251412834) links medication surveys to category-specific household spending; spending is not physical quantity, and real underlying records are unavailable. Neither supplies a national acreage-demand coefficient. |
| Organization: I-04/I-06/I-09 | Independent firms, contracts and ownership integration; capital, verification, losses, specifications and bargaining power. | [USDA risk-management strategies](https://www.ers.usda.gov/topics/farm-practices-management/risk-management/risk-management-strategies) discusses integration/contracting risks. Better coordination may help; lower costs, nutrient gains and producer capture remain separate hypotheses. |

P-06 connects land/capacity to delivery, prices and access. P-07 connects medication
use to category demand, then through recipes, feed, trade, stocks and contracts to
production. These remain open pathways until return rules close them. Imports may
buffer domestic supply while exporting land/water/emissions effects; report those
effects and the boundary of any omitted trade module.

## Stock/flow and nutrient formulation: F-09

Begin with regional segments; add parcel agents only for demonstrated need. Define
area stock `A[r,u]` for region `r` and exclusive physical use `u` in hectares, and
conversion flow `C[r,u,v]` in hectares/time:

```text
dA[r,u]/dt = sum_v C[r,v,u] - sum_v C[r,u,v]
total physical area[r] = sum_u A[r,u]
harvest[r,p] = sum_u A[r,u] * yield[r,u,p]
delivered nutrient[k] = sum_p edible delivery[p] * composition[p,k]
```

A fixed spatial boundary conserves total physical area, not total farm area.
Co-use is a site attribute, not another copy of its area. Yield is product
mass/hectare/time under actual use, with climate, water, technology and uncertainty
specified; it is not a universal land-quality multiplier. Rotations and multiple
harvests must reconcile to the same physical area and time interval. Impervious
conversion cannot restore production merely because demand recovers; restoration
requires an explicit feasible flow.

Edible delivery is mass/time after reconciling production, feed, processing,
imports/exports, losses and inventory changes (F-02). Composition has matching
nutrient-unit/edible-mass units. Keep components separate. Adequacy needs population
requirements and actual intake; health effects still require F-04 evidence.
Neither an acre nor nutrient density maps directly to life expectancy.

L-16 tests a balancing retention response where retention/restoration is feasible.
L-17 tests whether cumulative local harm affects subsequent development decisions.
Neither guarantees adequate supply or effective mitigation. Freeze each response
and compare alternatives using T-04/T-05.

## Farm decisions and distribution

[USDA farm typology](https://www.ers.usda.gov/topics/farm-economy/farm-structure-and-organization/farm-structure-and-contracting)
separates family ownership from scale and occupation; commercial farms can be
family owned. Represent ownership, enterprise, scale, tenure, contracts and
household dependence separately. Capture
[tenure and succession](https://ers.usda.gov/topics/farm-economy/land-use-land-value-tenure/farmland-ownership-and-tenure),
debt/liquidity, risk tolerance, horizon, stewardship, place attachment and community
continuity as candidate objectives/constraints under F-03. Their importance needs
interviews, surveys or observed choices. Never assign preferences from an ownership
label or dismiss a local concern as irrational.

Compare landowner lease/sale returns, farm margins, tenant security, worker
outcomes, food prices/access and nonparticipant effects separately. Profit-only
decisions are one structural alternative. Compare contracts and ownership
integration under equivalent product/nutrient specifications, including costs,
market power and risk allocation. Show tradeoffs or feasible frontiers; do not
invent a price for identity or combine all objectives into a single welfare score.

Run a separate nutrient-focused product-mix/recipe experiment. Define population
requirements and limiting-component constraints as a nutrient vector, with
affordability, access, processing losses and bioavailability where supported.
Compare feasible cost/input/nutrient frontiers against the reference basket;
do not assume one scalar nutrient score or that integration itself improves
composition. Measure delivery and sustained intake separately, and keep any
downstream health benefit conditional on its own evidence.

Lease payments, prices and lost private farm profit belong in actor accounts
(F-05/F-06), not automatically externalities. Preserve potential climate, water and
habitat effects (X-P01/X-P02/X-P06; X-N01/X-N02/X-N03) and uncompensated local network
effects (X-N07). Identify a beneficiary and feasible payer before claiming a
business opportunity.

## Learning exercise and future acceptance tests

Use a common reference, changing one lever at a time: development siting/footprint,
co-use, product-specific productivity, losses, demand mix including GLP-1 persistence,
contracts versus ownership integration, and nutrient-focused product/recipe mix.
Then compare combined changes. These are future experiment definitions, not
runnable menus.

Show national and regional views together: cumulative conversion and annual flows;
product capacity, edible delivery and adequacy; actor cash/risk; spillovers and
uncertainty. Commentary should explain binding constraints and reversal conditions.
A national buffer cannot hide a local shortage; a local shortage does not alone
establish a national food-security crisis. Test opposing beliefs B-50/B-51.

T-09 requires the following before this capability is claimed:

- Reconcile land stocks and conversion/restoration flows; no double counting co-use
  or electricity land serving a data center.
- Distinguish footprint, project boundary and annual conversion; retain uncertainty
  and source-definition/method changes.
- Compare a small national loss concentrated in a critical region with equal
  acreage on less productive land. Equal acres must not force equal outcomes.
- Test whether gains in a different crop, region or nutrient replace lost capacity;
  enforce water, logistics and fresh-food constraints.
- Distinguish spending, purchased mass and intake; validate substitution and
  discontinuation before translating demand into agricultural quantities.
- Reconcile feed, trade, losses and inventories; avoid duplicate integration
  payments or medication/diet health gains.
- Compare profit-only and evidence-supported constrained decisions; keep succession
  and community outcomes visible without assigning them by label.
- Preserve cases where integration raises cost, worsens access or fails to improve
  adequacy, including null and adverse results.
- Test nutrient-mix feasibility against needs, limiting components, budget and
  processing losses; a denser product must not guarantee adequate total intake.

After the v0.1 gate, select a product/region and appraise I-13 alongside relevant
I-02–I-11 records. Trace Q-05/RM-06 → L-16/L-17/P-06/P-07 → externalities → F-09/T-09
to evidence keys and implemented tests. This brief does not resolve the current
clinical calibration or causal dietary-effect gaps.
