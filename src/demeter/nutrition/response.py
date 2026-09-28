"""Inspectable delay and duration hypotheses; these are uncalibrated response mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, expm1, isfinite

from demeter.schema import EvidenceRegistry, Scenario

DYNAMIC_UNITS = {
    "diet_improvement_lag_years": "years",
    "diet_memory_years": "years",
    "diet_memory_weight": "fraction",
    "diet_recovery_lag_years": "years",
    "beta_upf_recovery": "log_multiplier_per_relative_exposure",
}
SATURATION_UNITS = {"diet_half_saturation": "relative_exposure"}
TIMING_KEYS = (
    "diet_lag_years",
    "diet_improvement_lag_years",
    "diet_memory_years",
    "diet_recovery_lag_years",
)


def response_units(scenario: Scenario) -> dict:
    if scenario.diet_response.kind == "legacy":
        return {}
    return {
        **DYNAMIC_UNITS,
        **(SATURATION_UNITS if scenario.diet_response.shape == "saturating" else {}),
    }


def relax(current: float, target: float, tau: float, dt: float) -> float:
    """Exact first-order response to a constant input; tau and dt are years."""
    if not all(isfinite(x) for x in (current, target, tau, dt)) or tau <= 0 or dt <= 0:
        raise ValueError("Response needs finite inputs, positive lag and duration")
    return current - expm1(-dt / tau) * (target - current)


def dose_shape(delta: float, shape: str, half_saturation: float | None = None) -> float:
    if not isfinite(delta):
        raise ValueError("Nonfinite dietary dose")
    if shape == "linear":
        return delta
    if (
        shape != "saturating"
        or half_saturation is None
        or not isfinite(half_saturation)
        or half_saturation <= 0
    ):
        raise ValueError("Saturating response requires a positive scale")
    # Same local derivative as linear; bounded magnitude with no invented threshold.
    return half_saturation * delta / (half_saturation + abs(delta))


@dataclass
class ResponseState:
    relative_upf: float = 1.0
    shaped_dose: float = 0.0
    progression_log: float = 0.0
    recovery_log: float = 0.0
    fast: float = 0.0
    memory: float = 0.0
    recovery: float = 0.0
    cumulative_exposure: float = 0.0
    cumulative_absolute_exposure: float = 0.0
    elapsed: float = 0.0


class DietaryResponse:
    def __init__(self, registry: EvidenceRegistry, scenario: Scenario):
        self.registry, self.spec = registry, scenario.diet_response
        self.state = ResponseState()
        for key, unit in {
            "diet_lag_years": "years",
            "beta_upf_progression": "log_multiplier_per_relative_exposure",
            **response_units(scenario),
        }.items():
            if (
                key not in registry.parameters
                or registry.parameters[key].unit != unit
                or registry.parameters[key].model_role != "health_model"
            ):
                raise ValueError(f"Missing response parameter, units or model role: {key}")
            value = registry.value(key)
            if not isfinite(value) or value < 0:
                raise ValueError(f"Invalid response parameter: {key}")
            if key in TIMING_KEYS and value <= 0:
                raise ValueError(f"Timing parameter must be positive: {key}")
        if self.spec.kind == "dynamic":
            if not 0 <= registry.value("diet_memory_weight") <= 1:
                raise ValueError("Dietary memory weight must be in [0,1]")
            if self.spec.shape == "saturating" and registry.value("diet_half_saturation") <= 0:
                raise ValueError("Dietary saturation scale must be positive")

    def advance(self, relative_upf: float, dt: float = 1) -> dict:
        if not isfinite(relative_upf) or relative_upf < 0 or not isfinite(dt) or dt <= 0:
            raise ValueError("Diet response needs nonnegative exposure and positive duration")
        p, s = self.registry.value, self.state
        delta = relative_upf - 1
        dose = dose_shape(
            delta,
            self.spec.shape,
            p("diet_half_saturation") if self.spec.shape == "saturating" else None,
        )
        if self.spec.kind == "legacy":
            # Keep the original log-state arithmetic, including step timing.
            s.fast = relax(s.fast, p("beta_upf_progression") * dose, p("diet_lag_years"), dt)
            progression_log, recovery_log = s.fast, 0.0
        else:
            tau = p("diet_improvement_lag_years") if dose < s.fast else p("diet_lag_years")
            s.fast = relax(s.fast, dose, tau, dt)
            s.memory = relax(s.memory, dose, p("diet_memory_years"), dt)
            s.recovery = relax(s.recovery, -dose, p("diet_recovery_lag_years"), dt)
            w = p("diet_memory_weight")
            progression_log = p("beta_upf_progression") * ((1 - w) * s.fast + w * s.memory)
            recovery_log = p("beta_upf_recovery") * s.recovery
        if max(abs(progression_log), abs(recovery_log)) > 50:
            raise ValueError("Scenario log effect is numerically unsupported")
        s.relative_upf, s.shaped_dose = relative_upf, dose
        s.progression_log, s.recovery_log = progression_log, recovery_log
        s.cumulative_exposure += delta * dt
        s.cumulative_absolute_exposure += abs(delta) * dt
        s.elapsed += dt
        return self.snapshot()

    def snapshot(self) -> dict:
        s = self.state
        return {
            "relative_upf": s.relative_upf,
            "shaped_dose": s.shaped_dose,
            "fast_response": s.fast,
            "retained_exposure": s.memory,
            "recovery_response": s.recovery,
            "cumulative_exposure_years": s.cumulative_exposure,
            "cumulative_absolute_exposure_years": s.cumulative_absolute_exposure,
            "applied_progression_multiplier": exp(s.progression_log),
            "applied_recovery_multiplier": exp(s.recovery_log),
            "elapsed_years": s.elapsed,
        }
