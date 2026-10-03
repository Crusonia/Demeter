# Public clinical evidence: October 3 source review

Three additional publications help refine the observation model. None supplies
an admitted U.S. clinical transition model. This is a used-source review: methods
and numerical summaries were visible before appraisal. It is not preregistration,
an independent holdout, or a parameter intake.

| Publication | What the inspected material supports | What remains unresolved |
| --- | --- | --- |
| [Shang et al., SNAC-K (2019)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6851857/) | Repeated glycemic assessment and registry deaths, including vital-status checks for dropouts. | Follow-up exclusions, changing assays, outcome-specific clocks, conflicting published summaries and event precedence. Individual records require permission. |
| [Choi et al., KoGES (2025)](https://onlinelibrary.wiley.com/doi/10.1111/joim.70010) | Repeated oral glucose tolerance tests and progression/recovery comparisons. | Missing glycemia is carried forward. A joint death/attrition likelihood is not established by the inspected main text. The supplement remains uninspected; records are available on request. |
| [Davoodian et al., ODCDC (2025)](https://doi.org/10.1016/S2214-109X(25)00237-2), [public article deposit](https://zenodo.org/records/18892123) | Pooled hidden-Markov transition analysis and a separate competing-risk analysis. | Follow-up exclusions, joint observation timing, uncertainty and transport require appraisal. The referenced appendix remains uninspected. Individual records are expressly not public. |

The [documentary receipt](validation/public-clinical-source-update-20261003-v1.json)
records original publication identities where acquired and rendered-source
locators where no original bytes were acquired. Publications remain fetch-only;
no article or participant records are redistributed. The ODCDC deposit date is
distinct from its publication year. Its overlap with earlier consortium work
does not establish independent validation.

These sources feed I-07/I-11/I-12 → F-08 → T-05/T-08 and the
[clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md). Before any
source-specific fit, resolve who enters each risk set, which event takes
precedence, how an unobserved visit differs from an observed unchanged state,
and which clocks survive source aggregation. Preserve discrepancies rather
than selecting a convenient version. A midpoint convention, fitted probability
or outcome-specific person-time rate is not automatically an annual generator
entry in Demeter.

The next admissible increment may be a limited observed-label/death comparator,
if its source definitions and sufficient statistics can be reconciled. No such
fit is implemented by this review. Public article access and permitted access
to individual observations are separate. No requests or contacts were made;
the public-source route continues without requiring institutional access.

No evidence parameter, initial population, dietary coefficient or engine
equation changes. Clinical fitting, direct initialization, engine activation,
sampling-distribution assumptions and scientific release remain unadmitted.
See [current model status](V0_1_STATUS.md) for the unresolved v0.1 requirements.
