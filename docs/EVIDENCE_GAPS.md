# Evidence needed to complete scientific v0.1

The data pipeline and model mechanics are usable. These remaining issues are scientific parameterization work. Synthetic values are retained visibly so the software can be tested, and scientific mode is disabled.

| Gate | Evidence available | Required resolution |
| --- | --- | --- |
| Age-specific baseline states | [Reloadable NHANES reconstruction](NHANES_PREVALENCE.md) supplies 2017-March 2020 adult age/sex glycemic shares, survey uncertainty, and 12 published diabetes cross-checks | Separate T2D from other diabetes; define observation-to-engine mapping, pediatric coverage, single-age interpolation and temporal transport |
| Prediabetes definition | The NHANES benchmark uses registered joint A1c/fasting-glucose criteria, with prior diagnosis taking precedence | Survey prediabetes does not identify all insulin resistance or broader metabolic health; resolve engine semantics explicitly |
| Transitions | [Rooney et al., 2021, ARIC](https://pubmed.ncbi.nlm.nih.gov/33555311/) follows older adults with several prediabetes definitions | Review corrected results and competing deaths; estimate hazards for the matched population, then obtain evidence for other ages |
| Diet effects | [Chen et al., 2023](https://pubmed.ncbi.nlm.nih.gov/36854188/) examines UPF and incident T2D in prospective cohorts | Match dose units, population, endpoint, covariates and lag; identify what is association versus a transportable causal effect |
| State mortality ratios | Aggregate NCHS mortality is reproduced; [public NHANES mortality linkage](LINKED_MORTALITY.md) now supplies a reloadable development-sample coverage audit | Specify baseline-versus-current-state estimands, age/sex support, linkage weighting, confounding and state changes before fitting excess hazards |
| Health backtest | A mortality persistence benchmark is implemented | Predeclare a historical health calibration period and a separate holdout; assess incidence/prevalence and mortality jointly |

## Why not use a published association as the current coefficient?

Chen et al. reports prospective T2D associations. It does not directly identify both H→IR and IR→T2D hazards in this three-state model. Applying a single reported ratio to both transitions would introduce an additional structural assumption. The present relative-exposure scenario also needs an explicit dose conversion. The synthetic coefficient therefore remains synthetic.

Rooney et al. studies an older ARIC population and compares alternative glycemic definitions. Its result cannot be treated as a national annual transition rate for every adult age. The PubMed record includes a correction that must be incorporated into extraction. This is useful candidate evidence; it is not yet an accepted parameterization.

These are matching and identification gaps, not a claim that no relevant literature exists. Record extracted estimates, uncertainty and transport assumptions in the registry before promoting parameters. Update tests and the release gate only after independent calibration/validation exists.
