from __future__ import annotations

import numpy as np

from demeter.data.baseline import baseline_validation, source_rows
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario


def mortality_backtest(train_year: int = 2022, holdout_year: int = 2023, sex: str = "all") -> dict:
    """Predeclared persistence benchmark: carry training qx/ax/tail into holdout year.

    This tests a frozen schedule forecast; no holdout values enter the prediction.
    It does not validate dietary effects or demographic/state transition hazards.
    """
    if train_year >= holdout_year:
        raise ValueError("holdout year must be later than training year")
    predicted = baseline_validation(train_year, sex)["calculated_e0"]
    observed = source_rows(holdout_year, sex)[0]["ex"]
    q0 = np.array([r["qx"] for r in source_rows(train_year, sex)[:-1]])
    q1 = np.array([r["qx"] for r in source_rows(holdout_year, sex)[:-1]])
    return {
        "method": "no-change mortality schedule persistence",
        "train_year": train_year,
        "holdout_year": holdout_year,
        "sex": sex,
        "predicted_e0": predicted,
        "observed_e0": observed,
        "error_years": predicted - observed,
        "qx_rmse": float(np.sqrt(np.mean((q0 - q1) ** 2))),
        "holdout_used_in_prediction": False,
        "scientific_validation_of_diet": False,
        "limitations": "Limited mortality benchmark; no fitted trend or dietary prediction. Source vintages are retrospective.",
    }


def prevalence_checks(registry: EvidenceRegistry) -> list[dict]:
    result = simulate(
        registry, Scenario(name="prevalence_validation", years=1, exposures={"upf": 1})
    )
    # Compare initial synthetic fractions, never quietly substitute total diabetes for T2D.
    specs = [
        ("observed_diabetes_20_39", "initial_t2d_share", "20–39"),
        ("observed_diabetes_40_59", "initial_t2d_share", "40–59"),
        ("observed_diabetes_60_plus", "initial_t2d_share", "60+"),
        ("observed_prediabetes_65_plus", "initial_ir_share", "65+"),
    ]
    return [
        {
            "benchmark": observed,
            "age_group": age,
            "observed": registry.value(observed),
            "model_initial": registry.value(initial),
            "absolute_difference": registry.value(initial) - registry.value(observed),
            "passed": False,
            "status": "unresolved_population_and_state_definition_match",
            "validation_only": result.validation_only,
        }
        for observed, initial, age in specs
    ]


def validate(registry: EvidenceRegistry) -> dict:
    audit = registry.audit()
    mortality = [
        baseline_validation(year, sex)
        for year in (2022, 2023, 2024)
        for sex in ("all", "male", "female")
    ]
    base = simulate(registry, Scenario(name="validation", years=25, exposures={"upf": 1}))
    max_residual = max(
        abs(r["population"] + r["cumulative_deaths"] - base.starting_population)
        for r in base.annual
    )
    scientific_ready = (
        False  # Alpha release has no independently validated health parameterization.
    )
    return {
        "software_checks_passed": all(r["passed"] for r in mortality) and max_residual < 1e-5,
        "scientific_release_ready": scientific_ready,
        "model_version": base.metadata["model_version"],
        "evidence": audit,
        "mortality_reconstruction": mortality,
        "max_population_accounting_error_people": max_residual,
        "prevalence": prevalence_checks(registry),
        "historical_backtest": mortality_backtest(),
        "status": "VALIDATION ONLY — NOT A SCIENTIFIC ESTIMATE",
    }
