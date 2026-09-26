# Contributing to Demeter

Demeter is an open-source project under [Food is Health](https://foodishealth.substack.com/). We welcome contributions that make the model more testable, reproducible, and useful—including evidence or mechanisms that challenge the project's initial hypotheses.

Use [GitHub issues](https://github.com/Crusonia/Demeter/issues) to propose a question or document a problem, and [pull requests](https://github.com/Crusonia/Demeter/pulls) for reviewable changes. Read [AGENTS.md](https://github.com/Crusonia/Demeter/blob/main/AGENTS.md) and the active phase objective before implementation work.

## Useful ways to contribute

| Background | Contributions |
| --- | --- |
| Research or clinical science | Operational health-state definitions, evidence reviews, causal critiques, reproducible calibration, or independent validation. |
| Economics or systems modeling | Price/substitution mechanisms, incentive design, delays, counterfactuals, uncertainty structure, or actor-specific accounting. |
| Farming, food, or healthcare operations | Real constraints, lead times, adoption frictions, costs, contracts, and examples where a proposed pathway fails. |
| Software or data engineering | Reproducible source transforms, typed interfaces, model diagnostics, meaningful tests, and clearer documentation. |
| Strategy or capital allocation | Explicit decision rights, feasible adaptive strategies, trigger conditions, and distinctions between social value and enterprise cash flow. |
| Food is Health readers | A sharply defined question, a sourced challenge, a competing explanation, or feedback on which model output would help a real decision. |

## Propose a research question

A useful issue states the question, actor, lever, outcome, and horizon. Describe the causal pathway, supporting sources, strongest competing explanation, and what observation would change the conclusion. Identify the current module or future phase it belongs to.

For a strategic option, additionally name the later choice, who can exercise it, what keeps it available, its cost and expiry, what information arrives, and what could prevent action. A market-size estimate alone is not a real-options specification.

## Add evidence

Provide a verifiable primary source or appropriate synthesis, exact definitions and units, population and period, uncertainty, and the transformation into a model input. Explain evidence strength and whether the relationship is causal, associational, mechanistic, or an assumption. Record relevant limitations and conflicting results.

Use public, permitted data and respect source licenses and access conditions. Do not commit identifiable personal health information. The repository's MIT License does not change the terms of third-party data.

## Change code or model semantics

Keep a change bounded and aligned with the current scientific gate. Preserve the separation between evidence, equations, and scenario assumptions. Document changed semantics, sources, validation results, and remaining uncertainty. Keep model behavior reproducible from the command line.

Use the repository's test and lint commands before proposing implementation changes. Tests should cover material invariants and failure modes rather than simply repeat the implementation. Synthetic data can validate software mechanics, but outputs that depend on it must remain labeled validation-only.

## Improve the public explanation

The public guide and wiki sources live in `docs/wiki/`, with the broader program rationale in `docs/PROJECT_VISION.md`. Keep the distinction between implemented capabilities and research directions explicit. Documentation should help readers follow the causal path and identify what evidence is missing.

Substack discussions can surface new questions. When a question enters the model, bring its definitions, sources, and assumptions into a reviewable issue or pull request so the reasoning remains inspectable.
