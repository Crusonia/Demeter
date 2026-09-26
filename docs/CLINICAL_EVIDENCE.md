# Clinical evidence appraisal for issue #1

These records advance extraction and traceability. They do not complete scientific
v0.1 and do not change any active model coefficient. Grade C marks useful
observational evidence with material transport and causal uncertainty.

## Corrected ARIC source

[Rooney et al. (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7871207/),
doi:10.1001/jamainternmed.2020.8774, follows older community participants from
2011–2013 through 2017. The source methods specify baseline ages 71–90.
The [April 2021 correction](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2778331)
(doi:10.1001/jamainternmed.2021.1321) replaces incorrectly calculated incidence rates.
The pinned PMC snapshot includes that correction; Table 2 was cross-checked against
the publisher's corrected article.

Extracted Table 2 values:

| Baseline definition and endpoint | Point | 95% CI | Registry unit |
| --- | ---: | --- | --- |
| HbA1c-defined prediabetes → total diabetes | 0.0228 | 0.0189–0.0275 | cases/person-year |
| HbA1c-defined prediabetes → mortality, relative to normoglycemia | 1.07 | 0.88–1.29 | hazard ratio |
| Fasting-glucose-defined prediabetes → mortality, relative to normoglycemia | 0.83 | 0.68–1.00 | hazard ratio |

Incidence is converted from per 1,000 person-years. Mortality ratios adjust for
age, sex, and race-center. Neither definition represents all insulin resistance; total
diabetes is not type-specific. Baseline-group incidence does not separately identify
the model's current-state progression, regression, and mortality hazards. These
observational ratios cannot establish the mortality benefit of changing state.

## LEADR source

[Koyama et al. (2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9021905/),
doi:10.1001/jamanetworkopen.2022.8158, analyzes clinical EHR observations from
2010–2018, with analysis in October 2021. The selected population is age 65+,
HbA1c-defined prediabetes, no kidney failure, and at least three months of follow-up.

| Table 2 group | Annualized rate | 95% CI |
| --- | ---: | --- |
| Overall | 0.053 | 0.051–0.054 |
| Baseline HbA1c 5.7–5.9% | 0.028 | 0.027–0.029 |
| Baseline HbA1c 6.0–6.4% | 0.082 | 0.079–0.084 |

Percent rates are divided by 100. The paper describes annualization by cases and
follow-up, and also reports incidence per person-year. These are not exact annual
Markov transition probabilities. The study cannot distinguish diabetes types and
does not represent the entire national population. The two HbA1c subgroups are
alternative strata, not independent effects to multiply together.

## Dietary identification remains unresolved

[Chen et al. (2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10300524/),
doi:10.2337/dc22-1993, reports prospective associations with incident T2D. Its
extreme-quintile comparison uses UPF as a share of food weight; the main Table 2
uses servings/day. Neither maps directly to Demeter's relative-exposure multiplier.
An incident-T2D association does not identify both healthy→IR and IR→T2D effects.
No number from this study has been promoted to the active UPF coefficient.

## Reproduction and interpretation

`demeter evidence verify-sources` checks each source's bytes against its SHA-256,
selects the registered table/row/column, and checks the point estimate and both CI
limits after the declared scale transform. Errors fail closed. HTML files remain
in ignored raw storage. `--download` only fetches missing files; changing a source
pin requires a reviewed registry edit. The default command does not access the
network. The committed verification receipt records a successful real-source run.

An extraction pass establishes what was read. It does not establish national
transportability, causal identification, calibration, or independent validation.
No averaging of ARIC and LEADR is justified here. All active health coefficients
remain synthetic, and scientific mode remains blocked.
