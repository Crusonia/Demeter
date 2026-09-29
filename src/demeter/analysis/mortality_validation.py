"""Frozen temporal prediction checks; no estimation or engine-parameter promotion."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from demeter.analysis.mortality_development import contributions
from demeter.data.ingest import digest
from demeter.data.linked_mortality import read_mortality
from demeter.data.nhanes import classify, read_xpt
from demeter.schema import EvidenceRegistry

PROTOCOL = Path("docs/validation/mortality-validation-protocol-v1.json")
AMENDMENT = Path("docs/validation/mortality-validation-implementation-amendment-1.json")
INTERPRETER = "src/demeter/analysis/mortality_validation.py"
STORE = Path("data/sources/nhanes-mortality/2013-2014")
MODELS = ("glycemic", "null", "glycemic_piecewise", "null_piecewise")
STATES = ("normoglycemia", "prediabetes", "diabetes_any_type")


def implementation_amendment(root: Path, spec: dict, protocol: dict) -> dict | None:
    """Preserve the original freeze while disclosing a pinned post-intake guard fix."""
    reference = spec.get("implementation_amendment")
    if reference is None:
        return None
    if reference["path"] != AMENDMENT.as_posix():
        raise ValueError("Unknown implementation amendment")
    content = (root / AMENDMENT).read_bytes()
    if digest(content) != reference["sha256"]:
        raise ValueError("Implementation amendment checksum mismatch")
    amendment = json.loads(content)
    if (
        amendment["schema_version"] != 1
        or amendment["protocol_sha256"] != spec["protocol_sha256"]
        or amendment["original_file_sha256"] != protocol["protected_files"][INTERPRETER]
        or amendment["file"] != INTERPRETER
        or amendment["numerical_methods_changed"] is not False
        or amendment["outcomes_already_inspected"] is not True
    ):
        raise ValueError("Invalid post-intake implementation amendment")
    return amendment


def load_protocol(root: Path = Path("."), registry: EvidenceRegistry | None = None) -> dict:
    """Fail before parsing outcomes if the preregistered contract has drifted."""
    registry = registry or EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    spec = registry.datasets["mortality_validation"]
    content = (root / PROTOCOL).read_bytes()
    if (
        spec["model_role"] != "prediction_benchmark_only"
        or digest(content) != spec["protocol_sha256"]
    ):
        raise ValueError("Frozen mortality protocol mismatch")
    protocol = json.loads(content)
    if protocol["schema_version"] != 1 or protocol["validation_cycle"] != "2013-2014":
        raise ValueError("Invalid mortality validation scope")
    if set(protocol["models"]) != set(MODELS):
        raise ValueError("All four frozen models are required")
    protected = dict(protocol["protected_files"])
    amendment = implementation_amendment(root, spec, protocol)
    if amendment:
        protected[INTERPRETER] = amendment["amended_file_sha256"]
    for path, sha in protected.items():
        if digest((root / path).read_bytes()) != sha:
            raise ValueError(f"Frozen implementation or development receipt changed: {path}")
    for key, value in protocol["parameter_contract"].items():
        if registry.parameters[key].model_dump(mode="json") != value:
            raise ValueError(f"Frozen coefficient metadata changed: {key}")
    if registry.datasets["mortality_development"] != protocol["development_specification"]:
        raise ValueError("Frozen development specification changed")
    if registry.datasets["nhanes_glycemic_prevalence"]["analysis"] != protocol["glycemic_analysis"]:
        raise ValueError("Frozen glycemic observation definition changed")
    return protocol


def read_validation_store(protocol: dict, source: Path = STORE) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((source / "manifest.json").read_bytes())
    if (
        manifest["schema_version"] != 1
        or manifest["cycle"] != protocol["validation_cycle"]
        or set(manifest["sources"]) != set(protocol["sources"])
    ):
        raise ValueError("Unexpected reserved-cycle source manifest")
    # The protocol artifact has a canonical JSON encoding established by the
    # freeze script. Check its identity before opening even the first source.
    protocol_bytes = (json.dumps(protocol, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if manifest.get("protocol_sha256") != digest(protocol_bytes):
        raise ValueError("Reserved intake belongs to a different frozen protocol")
    for name, expected in protocol["sources"].items():
        receipt = manifest["sources"][name]
        if (
            receipt["url"] != expected["url"]
            or digest((source / name).read_bytes()) != receipt["sha256"]
        ):
            raise ValueError(f"Reserved source identity/checksum mismatch: {name}")
    frame = read_xpt(source / "DEMO_H.xpt", protocol["columns"]["DEMO_H.xpt"])
    mortality = read_mortality(source / protocol["mortality_file"])
    if set(frame.SEQN) != set(mortality.SEQN):
        raise ValueError("Reserved mortality and demographic cycle IDs do not match")
    frame = frame.merge(mortality, on="SEQN", validate="one_to_one")
    for name, columns in protocol["columns"].items():
        if name == "DEMO_H.xpt":
            continue
        table = read_xpt(source / name, columns)
        if not table.SEQN.isin(frame.SEQN).all():
            raise ValueError(f"Unknown reserved-cycle ID in {name}")
        frame = frame.merge(table, on="SEQN", how="left", validate="one_to_one")
    return frame, manifest


def survey_variance(influence, domain, design) -> dict:
    """WR Taylor variance: retain zero-domain PSUs, use domain support for df."""
    influence = np.asarray(influence, dtype=float)
    domain = np.asarray(domain, dtype=bool)
    if (
        len(influence) != len(domain)
        or len(domain) != len(design)
        or not np.isfinite(influence).all()
        or not np.isfinite(design.to_numpy()).all()
        or np.any(influence[~domain] != 0)
    ):
        raise ValueError("Invalid linearized survey contributions/design")
    totals = (
        pd.DataFrame({"u": influence, "represented": domain.astype(int)})
        .groupby([design.SDMVSTRA.to_numpy(), design.SDMVPSU.to_numpy()])
        .sum()
    )
    variance, design_df, domain_df = 0.0, 0, 0
    for _, group in totals.groupby(level=0):
        count = len(group)
        if count < 2:
            raise ValueError("Singleton full-design stratum")
        values = group.u.to_numpy()
        variance += count / (count - 1) * float(np.sum((values - values.mean()) ** 2))
        design_df += count - 1
        domain_df += max(int((group.represented > 0).sum()) - 1, 0)
    return {
        "variance": variance,
        "standard_error": float(np.sqrt(variance)),
        "design_degrees_of_freedom": design_df,
        "domain_degrees_of_freedom": domain_df,
        "represented_psus": int((totals.represented > 0).sum()),
    }


def _validate_vectors(weight, domain, values):
    weight, domain = np.asarray(weight, dtype=float), np.asarray(domain, dtype=bool)
    if len(weight) != len(domain) or not np.isfinite(weight).all() or (weight <= 0).any():
        raise ValueError("Positive finite survey weights and matching domain required")
    arrays = [np.asarray(value, dtype=float) for value in values]
    if any(len(value) != len(weight) or not np.isfinite(value[domain]).all() for value in arrays):
        raise ValueError("Invalid values in the selected domain")
    return weight, domain, arrays


def survey_mean(values, weight, domain, design, confidence_level) -> dict:
    weight, domain, (values,) = _validate_vectors(weight, domain, [values])
    if not 0 < confidence_level < 1:
        raise ValueError("Invalid confidence level")
    if not domain.any():
        return {"estimate": None, "interval": None, "unavailable_reason": "empty_domain"}
    w, y = weight[domain], values[domain]
    mean = float(y[0]) if np.ptp(y) == 0 else float(w @ y / w.sum())
    influence = np.zeros(len(weight))
    influence[domain] = w * (y - mean) / w.sum()
    result = {"estimate": mean, **survey_variance(influence, domain, design)}
    df = result["domain_degrees_of_freedom"]
    half = (
        student_t.ppf((1 + confidence_level) / 2, df) * result["standard_error"] if df > 0 else None
    )
    result.update(
        interval=[mean - half, mean + half] if half is not None and np.isfinite(half) else None,
        unavailable_reason=None
        if half is not None and np.isfinite(half)
        else "insufficient_domain_df",
    )
    return result


def event_ratio(event, intensity, weight, domain, design, confidence_level) -> dict:
    weight, domain, (event, intensity) = _validate_vectors(weight, domain, [event, intensity])
    if not 0 < confidence_level < 1 or not np.isin(event[domain], [0, 1]).all():
        raise ValueError("Invalid interval level or event indicator")
    if (intensity[domain] < 0).any():
        raise ValueError("Negative event intensity")
    observed, expected = (
        float(weight[domain] @ event[domain]),
        float(weight[domain] @ intensity[domain]),
    )
    result = {"observed_weighted_events": observed, "expected_weighted_event_intensity": expected}
    if not domain.any() or expected <= 0:
        return {
            **result,
            "estimate": None,
            "interval": None,
            "unavailable_reason": "empty_domain_or_zero_intensity",
        }
    ratio = observed / expected
    influence = np.zeros(len(weight))
    influence[domain] = weight[domain] * (event[domain] - ratio * intensity[domain]) / expected
    result.update(estimate=ratio, **survey_variance(influence, domain, design))
    df = result["domain_degrees_of_freedom"]
    result.update(
        interval=None,
        unavailable_reason="no_observed_events" if observed == 0 else "insufficient_domain_df",
    )
    if observed > 0 and df > 0:
        half = student_t.ppf((1 + confidence_level) / 2, df) * result["standard_error"] / ratio
        with np.errstate(over="ignore"):
            bounds = np.exp(np.log(ratio) + np.array([-half, half]))
        result.update(
            interval=bounds.tolist() if np.isfinite(bounds).all() else None,
            unavailable_reason=None if np.isfinite(bounds).all() else "nonfinite_interval",
        )
    return result


def prepare_sample(frame: pd.DataFrame, protocol: dict):
    a, spec = protocol["glycemic_analysis"], protocol["development_specification"]
    sample = frame.loc[np.isfinite(frame.WTSAF2YR) & (frame.WTSAF2YR > 0)].copy()
    states = classify(sample, a)
    keep = np.ones(len(sample), dtype=bool)
    criteria = {
        "under_adult_minimum": sample.RIDAGEYR >= a["adult_age_min"],
        "known_pregnancy": ~(
            (sample.RIDEXPRG == 1) & (sample.RIDAGEYR <= a["pregnancy_exclusion_age_max"])
        ),
        "missing_glycemia": states.notna(),
        "linkage_ineligible": sample.ELIGSTAT == 1,
        "topcoded_age": sample.RIDAGEYR < spec["topcoded_age"],
        "missing_sex": sample.RIAGENDR.isin([1, 2]),
        "missing_or_zero_followup": np.isfinite(sample.PERMTH_EXM) & (sample.PERMTH_EXM > 0),
    }
    exclusions = {}
    for reason, valid in criteria.items():
        exclusions[reason] = int((keep & ~valid.to_numpy()).sum())
        keep &= valid.to_numpy()
    if not keep.any():
        raise ValueError("Empty reserved analysis population")
    selected = sample.loc[keep]
    event = selected.MORTSTAT.to_numpy()
    if not np.isin(event, [0, 1]).all():
        raise ValueError("Missing/bad eligible vital status")
    x = np.column_stack(
        [
            np.ones(len(selected)),
            selected.RIDAGEYR - a["adult_age_min"],
            selected.RIAGENDR == 1,
            states.loc[keep] == "prediabetes",
            states.loc[keep] == "diabetes_any_type",
        ]
    ).astype(float)
    return sample, states, keep, x, exclusions


def evaluate(frame: pd.DataFrame, protocol: dict) -> dict:
    """Evaluate every frozen model without touching optimizer or training records."""
    a, spec = protocol["glycemic_analysis"], protocol["development_specification"]
    sample, states, eligible, x, exclusions = prepare_sample(frame, protocol)
    time = sample.loc[eligible, "PERMTH_EXM"].to_numpy() / spec["months_per_year"]
    event = np.zeros(len(sample))
    event[eligible] = sample.loc[eligible, "MORTSTAT"]
    weight, design = sample.WTSAF2YR.to_numpy(), sample[["SDMVSTRA", "SDMVPSU"]]
    domains = [("overall", "all", "all", eligible)]
    for group in a["age_groups"]:
        age = (sample.RIDAGEYR >= group["min"]) & (
            True if group["max"] is None else sample.RIDAGEYR <= group["max"]
        )
        for sex, code in (("all", None), ("male", 1), ("female", 2)):
            for state in STATES:
                mask = (
                    eligible
                    & age.to_numpy()
                    & (True if code is None else (sample.RIAGENDR == code).to_numpy())
                    & (states == state).to_numpy()
                )
                domains.append((group["id"], sex, state, mask))
    predictions = {}
    for name in MODELS:
        model_x = x[:, : 3 if name.startswith("null") else 5]
        age_knot = None
        if name.endswith("_piecewise"):
            age_knot = spec["alternative_age"]["knot_age"] - a["adult_age_min"]
            model_x = np.column_stack([model_x, np.maximum(x[:, 1] - age_knot, 0)])
        coefficients = np.asarray(protocol["models"][name]["coefficients"])
        ll, _, _, hazard = contributions(
            coefficients, model_x, time, event[eligible], spec["integration"], age_knot
        )
        score, intensity = np.zeros(len(sample)), np.zeros(len(sample))
        score[eligible], intensity[eligible] = ll, hazard
        predictions[name] = (score, intensity)
    result = {
        "schema_version": 1,
        "model_role": "prediction_benchmark_only",
        "validation_only": True,
        "scientific_release_ready": False,
        "independent_prediction_evaluated": False,
        "clinical_acceptance": "unresolved; no clinical tolerances declared",
        "uncertainty_scope": protocol["uncertainty_scope"],
        "counts": {
            "source_n": len(frame),
            "positive_weight_n": len(sample),
            "included_n": int(eligible.sum()),
            "deaths_n": int(event.sum()),
            "sequential_exclusions": exclusions,
        },
        "followup_years": {
            "min": float(time.min()),
            "max": float(time.max()),
            "weighted_mean": float(np.average(time, weights=weight[eligible])),
        },
        "models": {},
        "comparisons": {},
        "limitations": protocol["limitations"],
    }
    for name, (score, intensity) in predictions.items():
        rows = []
        for age, sex, state, mask in domains:
            months = sample.loc[mask, "PERMTH_EXM"]
            rows.append(
                {
                    "age_group": age,
                    "sex": sex,
                    "baseline_state": state,
                    "n": int(mask.sum()),
                    "deaths": int(event[mask].sum()),
                    "followup_months_min": float(months.min()) if mask.any() else None,
                    "followup_months_max": float(months.max()) if mask.any() else None,
                    "event_intensity_ratio": event_ratio(
                        event, intensity, weight, mask, design, a["confidence_level"]
                    ),
                    "mean_log_score": survey_mean(
                        score, weight, mask, design, a["confidence_level"]
                    ),
                }
            )
        result["models"][name] = {"domains": rows}
    for left, right in protocol["comparisons"]:
        difference = predictions[left][0] - predictions[right][0]
        result["comparisons"][left + "_minus_" + right] = [
            {
                "age_group": age,
                "sex": sex,
                "baseline_state": state,
                "n": int(mask.sum()),
                **survey_mean(difference, weight, mask, design, a["confidence_level"]),
            }
            for age, sex, state, mask in domains
        ]
    return result


def validation_report(root: Path = Path(".")) -> dict:
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    protocol = load_protocol(root, registry)
    frame, manifest = read_validation_store(protocol, root / STORE)
    protocol_sha = digest((root / PROTOCOL).read_bytes())
    if manifest["protocol_sha256"] != protocol_sha:
        raise ValueError("Reserved intake belongs to a different frozen protocol")
    report = evaluate(frame, protocol)
    report["independent_prediction_evaluated"] = True
    report["provenance"] = {
        "protocol_sha256": protocol_sha,
        "protocol_freeze_commit": manifest["protocol_freeze_commit"],
        "evidence_sha256": registry.content_hash,
        "source_sha256": {name: row["sha256"] for name, row in manifest["sources"].items()},
        "source_manifest_sha256": digest((root / STORE / "manifest.json").read_bytes()),
        "frozen_models": protocol["models"],
        "protected_implementation": protocol["protected_files"],
    }
    amendment = implementation_amendment(root, registry.datasets["mortality_validation"], protocol)
    if amendment:
        report["provenance"]["implementation_amendment"] = {
            "path": AMENDMENT.as_posix(),
            "sha256": digest((root / AMENDMENT).read_bytes()),
            "record": amendment,
        }
        report["provenance"]["executed_implementation"] = {
            **protocol["protected_files"],
            INTERPRETER: amendment["amended_file_sha256"],
        }
    return report
