"""Replay unchanged synthetic inputs under the additive CTMC numerical contract."""

from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from demeter.analysis.longitudinal_likelihood_validation import (
    AMENDMENT_PATH,
    AMENDMENT_SHA256,
    DATASET,
    likelihood_software_report,
    load_likelihood_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REPLAY_PATH = "docs/validation/longitudinal-probability-contract-replay-v2.json"
REPLAY_SHA256 = "297d290b5e203f60fc420ad102cd5b7c35bd1e9da6a13ea785ee64eac0621e43"


def _pinned(path, expected):
    content = (ROOT / path).read_bytes()
    if sha256(content).hexdigest() != expected:
        raise ValueError("Numerical replay artifact checksum mismatch")
    return json.loads(content)


def _original_math(report, *, current):
    result = deepcopy(report)
    result.pop("provenance")
    if current:
        for contribution in result["contributions"].values():
            contribution.pop("numerical_input_deviations")
    return json.loads(json.dumps(result, allow_nan=False))


def _matches(actual, expected, tolerance, log_tolerance=None):
    if type(expected) is dict:
        return (
            type(actual) is dict
            and set(actual) == set(expected)
            and all(
                _matches(
                    actual[key],
                    value,
                    log_tolerance
                    if key == "log_likelihood" and log_tolerance is not None
                    else tolerance,
                    log_tolerance,
                )
                for key, value in expected.items()
            )
        )
    if type(expected) is list:
        return (
            type(actual) is list
            and len(actual) == len(expected)
            and all(
                _matches(x, y, tolerance, log_tolerance)
                for x, y in zip(actual, expected, strict=True)
            )
        )
    if type(expected) in (int, float):
        return (
            type(actual) in (int, float)
            and isfinite(actual)
            and abs(actual - expected) <= tolerance
        )
    return type(actual) is type(expected) and actual == expected


def verify():
    """Read only software artifacts/registered toy inputs; never participant sources."""
    amendment = _pinned(AMENDMENT_PATH, AMENDMENT_SHA256)
    receipt = _pinned(REPLAY_PATH, REPLAY_SHA256)
    original_spec = amendment["preserved_original_report"]
    original = _pinned(original_spec["path"], original_spec["sha256"])
    if receipt["amendment_sha256"] != AMENDMENT_SHA256:
        raise ValueError("Numerical replay parent mismatch")
    for name, expected in receipt["current_implementation_sha256"].items():
        if sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Numerical replay implementation checksum mismatch")
    registry = load_likelihood_registry(ROOT / "evidence/parameters.yaml")
    names = original["provenance"]["registered_inputs"]
    scope = {
        "parameters": {name: registry.parameters[name].model_dump(mode="json") for name in names},
        "dataset": registry.datasets[DATASET],
    }
    canonical = json.dumps(scope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if sha256(canonical).hexdigest() != receipt["registered_scope_sha256"]:
        raise ValueError("Numerical replay registered input provenance mismatch")
    current = likelihood_software_report(registry)
    if current["software_checks_passed"] is not True:
        raise ValueError("Current numerical replay failed")
    tolerance = registry.value("longitudinal_probability_absolute_tolerance")
    log_tolerance = registry.value("longitudinal_log_likelihood_absolute_tolerance")
    if not _matches(
        _original_math(current, current=True),
        _original_math(original, current=False),
        tolerance,
        log_tolerance,
    ):
        raise ValueError("Original mathematical results changed beyond their registered tolerance")
    if any(
        current[key] is not False
        for key in (
            "clinical_fit_allowed",
            "clinical_fit_performed",
            "engine_activation_allowed",
            "engine_parameters_updated",
            "scientific_release_ready",
            "independent_prediction_performed",
        )
    ):
        raise ValueError("Numerical replay cannot promote scientific eligibility")
    return current


if __name__ == "__main__":
    try:
        verify()
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        print("CTMC numerical replay: FAIL; no scientific activation")
        raise SystemExit(1) from None
    print("CTMC numerical replay: PASS; unchanged registered fixture, no clinical fit")
