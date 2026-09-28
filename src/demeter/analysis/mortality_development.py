"""Survey-weighted development benchmark; no clinical or engine parameter promotion."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import t as student_t

from demeter.data.linked_mortality import definition, read_store
from demeter.data.nhanes import classify
from demeter.schema import EvidenceRegistry


def integrated_moments(time, slope, *, threshold, terms):
    """Return integrals of exp(slope*t) * (1, t, t**2) from zero to time.

    The series near zero avoids cancellation and supplies the exact zero-slope
    limit. These are analytic hazard integrals, not discrete time approximations.
    """
    time = np.asarray(time, dtype=float)
    if not np.isfinite(time).all() or (time < 0).any() or not np.isfinite(slope):
        raise ValueError("Invalid follow-up or age slope")
    z = slope * time
    small = np.abs(z) < threshold
    result = np.empty((len(time), 3))
    for power in range(3):
        term = np.ones(int(small.sum()))
        total = term / (power + 1)
        for k in range(1, terms):
            term = term * z[small] / k
            total += term / (k + power + 1)
        result[small, power] = time[small] ** (power + 1) * total
    u = z[~small]
    e = np.exp(u)
    result[~small, 0] = time[~small] * np.expm1(u) / u
    result[~small, 1] = time[~small] ** 2 * (e * (u - 1) + 1) / u**2
    result[~small, 2] = time[~small] ** 3 * (e * (u**2 - 2 * u + 2) - 2) / u**3
    return result


def contributions(beta, x, time, event, integration, age_knot=None):
    """Per-person log likelihood, score, negative Hessian and cumulative hazard.

    Column one is baseline age centered at the registered adult minimum.
    Follow-up adds attained age continuously to that column.
    """
    if age_knot is not None:
        return piecewise_contributions(beta, x, time, event, integration, age_knot)
    moments = integrated_moments(
        time, beta[1], threshold=integration["series_threshold"], terms=integration["series_terms"]
    )
    eta = x @ beta
    scaled = np.exp(eta)[:, None] * moments
    hazard = scaled[:, 0]
    gradient = hazard[:, None] * x
    gradient[:, 1] += scaled[:, 1]
    information = hazard[:, None, None] * x[:, :, None] * x[:, None, :]
    information[:, :, 1] += scaled[:, 1, None] * x
    information[:, 1, :] += scaled[:, 1, None] * x
    information[:, 1, 1] += scaled[:, 2]
    event_x = x.copy()
    event_x[:, 1] += time
    score = event[:, None] * event_x - gradient
    log_likelihood = event * (eta + beta[1] * time) - hazard
    if not all(np.isfinite(v).all() for v in (log_likelihood, score, information, hazard)):
        raise ValueError("Nonfinite survival likelihood; fit is invalid")
    return log_likelihood, score, information, hazard


def piecewise_contributions(beta, x, time, event, integration, age_knot):
    """Exact continuous log-hazard hinge; final design column is attained-age hinge.

    age_knot uses the same centered age coordinate as x[:, 1]. The integral is
    split when an individual crosses the knot, including crossings in follow-up.
    """
    before = np.minimum(time, np.maximum(age_knot - x[:, 1], 0))
    after = time - before
    hazard = np.zeros(len(time))
    gradient = np.zeros_like(x)
    information = np.zeros((len(time), len(beta), len(beta)))
    for duration, start, above in ((before, np.zeros(len(time)), False), (after, before, True)):
        start_x = x.copy()
        start_x[:, 1] += start
        start_x[:, -1] = np.maximum(start_x[:, 1] - age_knot, 0)
        growth = np.zeros(len(beta))
        growth[1] = 1
        growth[-1] = int(above)
        moments = integrated_moments(
            duration,
            float(beta @ growth),
            threshold=integration["series_threshold"],
            terms=integration["series_terms"],
        )
        scaled = np.exp(start_x @ beta)[:, None] * moments
        h, first, second = scaled.T
        hazard += h
        gradient += h[:, None] * start_x + first[:, None] * growth
        information += (
            h[:, None, None] * start_x[:, :, None] * start_x[:, None, :]
            + first[:, None, None]
            * (
                start_x[:, :, None] * growth[None, None, :]
                + growth[None, :, None] * start_x[:, None, :]
            )
            + second[:, None, None] * growth[None, :, None] * growth[None, None, :]
        )
    event_x = x.copy()
    event_x[:, 1] += time
    event_x[:, -1] = np.maximum(event_x[:, 1] - age_knot, 0)
    ll = event * (event_x @ beta) - hazard
    score = event[:, None] * event_x - gradient
    if not all(np.isfinite(v).all() for v in (ll, score, information, hazard)):
        raise ValueError("Nonfinite piecewise survival likelihood; fit is invalid")
    return ll, score, information, hazard


def survey_covariance(information, scores, design):
    """Linearized score sandwich retaining every design PSU, even empty domains."""
    if len(scores) != len(design) or not np.isfinite(design.to_numpy()).all():
        raise ValueError("Missing or incompatible survey design")
    if np.linalg.eigvalsh(information).min() <= 0:
        raise ValueError("Unidentified survival information matrix")
    totals = (
        pd.DataFrame(scores).groupby([design.SDMVSTRA.to_numpy(), design.SDMVPSU.to_numpy()]).sum()
    )
    meat = np.zeros_like(information)
    df = 0
    for _, group in totals.groupby(level=0):
        m = len(group)
        if m < 2:
            raise ValueError("Singleton survey stratum")
        centered = group.to_numpy() - group.to_numpy().mean(axis=0)
        meat += m / (m - 1) * centered.T @ centered
        df += m - 1
    bread = np.linalg.inv(information)
    covariance = bread @ meat @ bread.T
    if not np.isfinite(covariance).all() or np.linalg.matrix_rank(meat) < len(information):
        raise ValueError("Unidentified survey covariance")
    return (covariance + covariance.T) / 2, df


def fit(x, time, event, weight, domain, design, spec, *, age_knot=None):
    """Fit with supplied design kept intact; arrays x/time/event describe domain only."""
    domain = np.asarray(domain, dtype=bool)
    weight = np.asarray(weight, dtype=float)
    if len(weight) != len(domain) or not np.isfinite(weight).all() or (weight <= 0).any():
        raise ValueError("Positive finite survey weights required")
    if len(x) != domain.sum() or len(time) != len(x) or len(event) != len(x):
        raise ValueError("Incompatible survival domain")
    if not len(x) or not np.isfinite(x).all() or np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError("Empty or unidentified survival domain")
    if (time <= 0).any() or not np.isfinite(time).all() or not np.isin(event, [0, 1]).all():
        raise ValueError("Observed positive follow-up and binary vital status required")
    if event.sum() == 0:
        raise ValueError("No observed deaths; intercept unidentified")
    w = weight[domain] / weight[domain].sum()
    start = np.zeros(x.shape[1])
    start[0] = np.log(np.dot(w, event) / np.dot(w, time))

    def evaluate(beta):
        ll, score, info, _ = contributions(beta, x, time, event, spec["integration"], age_knot)
        return -w @ ll, -(w @ score), np.einsum("i,ijk->jk", w, info)

    numerical = spec["optimizer"]
    result = minimize(
        lambda b: evaluate(b)[:2],
        start,
        jac=True,
        hess=lambda b: evaluate(b)[2],
        method=numerical["method"],
        options={
            "gtol": numerical["gradient_tolerance"],
            "maxiter": numerical["maximum_iterations"],
        },
    )
    ll, score, info, hazard = contributions(result.x, x, time, event, spec["integration"], age_knot)
    gradient = float(np.linalg.norm(w @ score))
    if not result.success or gradient > numerical["gradient_tolerance"]:
        raise ValueError(f"Survival fit did not converge: {result.message}; gradient={gradient}")
    information = np.einsum("i,ijk->jk", w, info)
    all_scores = np.zeros((len(domain), x.shape[1]))
    all_scores[domain] = w[:, None] * score
    covariance, df = survey_covariance(information, all_scores, design)
    return {
        "coefficients": result.x.tolist(),
        "covariance": covariance.tolist(),
        "degrees_of_freedom": df,
        "information_condition_number": float(np.linalg.cond(information)),
        "gradient_norm": gradient,
        "iterations": int(result.nit),
        "weighted_mean_log_likelihood": float(w @ ll),
        "observed_weighted_events": float(weight[domain] @ event),
        "expected_weighted_event_intensity": float(weight[domain] @ hazard),
        "observed_expected_ratio": float((w @ event) / (w @ hazard)),
    }


def development_report(registry: EvidenceRegistry) -> dict:
    spec = registry.datasets["mortality_development"]
    if (
        spec["model_role"] != "development_benchmark_only"
        or spec["development_cycle"] != "2011-2012"
    ):
        raise ValueError("Unapproved development scope")
    frame, sources = read_store()
    a = definition(registry)["glycemic_analysis"]
    sample = frame.loc[np.isfinite(frame.WTSAF2YR) & (frame.WTSAF2YR > 0)].copy()
    states = classify(sample, a)
    domain = pd.Series(True, index=sample.index)
    exclusions = {}
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
    for reason, keep in criteria.items():
        exclusions[reason] = int((domain & ~keep).sum())
        domain &= keep
    selected = sample.loc[domain]
    time = selected.PERMTH_EXM.to_numpy() / spec["months_per_year"]
    event = selected.MORTSTAT.to_numpy()
    x = np.column_stack(
        [
            np.ones(len(selected)),
            selected.RIDAGEYR - a["adult_age_min"],
            selected.RIAGENDR == 1,
            states.loc[domain] == "prediabetes",
            states.loc[domain] == "diabetes_any_type",
        ]
    ).astype(float)
    report = {
        "validation_only": True,
        "scientific_release_ready": False,
        "independent_validation_performed": False,
        "evidence_sha256": registry.content_hash,
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "specification": spec,
        "glycemic_analysis": a,
        "source_sha256": {k: v["sha256"] for k, v in sources["sources"].items()},
        "counts": {
            "positive_weight_n": len(sample),
            "included_n": len(selected),
            "deaths_n": int(event.sum()),
            "sequential_exclusions": exclusions,
        },
        "models": {},
        "limitations": [
            "Development fit only; the reserved cycle has not been evaluated.",
            "Baseline glycemic categories do not identify engine state mortality or causal effects.",
            "Unadjusted complete-case/linkage selection and public follow-up perturbation remain unresolved.",
            "Adults below the public age top-code only; no pediatric or oldest-age transport.",
            "Intervals cover design-based sampling variation, not confounding or structural uncertainty.",
            "In-sample likelihood gain and event balance are fit diagnostics, not validation.",
            "Expected event intensity integrates fitted hazard over actual observed risk time; it is not risk at a common horizon.",
        ],
    }
    for model, width in (
        ("glycemic", 5),
        ("null", 3),
        ("glycemic_piecewise", 5),
        ("null_piecewise", 3),
    ):
        model_x = x[:, :width]
        age_knot = None
        if model.endswith("_piecewise"):
            age_knot = spec["alternative_age"]["knot_age"] - a["adult_age_min"]
            model_x = np.column_stack([model_x, np.maximum(x[:, 1] - age_knot, 0)])
        fitted = fit(
            model_x,
            time,
            event,
            sample.WTSAF2YR.to_numpy(),
            domain.to_numpy(),
            sample[["SDMVSTRA", "SDMVPSU"]],
            spec,
            age_knot=age_knot,
        )
        fitted["coefficient_keys"] = spec["coefficients"][model]
        half_width = student_t.ppf(
            (1 + a["confidence_level"]) / 2, fitted["degrees_of_freedom"]
        ) * np.sqrt(np.diag(fitted["covariance"]))
        fitted["intervals"] = [
            [float(b - h), float(b + h)]
            for b, h in zip(fitted["coefficients"], half_width, strict=True)
        ]
        _, _, _, intensity = contributions(
            np.array(fitted["coefficients"]), model_x, time, event, spec["integration"], age_knot
        )
        fitted["development_domains"] = []
        for group in a["age_groups"]:
            age = (selected.RIDAGEYR >= group["min"]) & (
                True if group["max"] is None else selected.RIDAGEYR <= group["max"]
            )
            for sex, code in (("all", None), ("male", 1), ("female", 2)):
                for state in ("normoglycemia", "prediabetes", "diabetes_any_type"):
                    d = (
                        age
                        & (True if code is None else selected.RIAGENDR == code)
                        & (states.loc[domain] == state)
                    ).to_numpy()
                    w = selected.WTSAF2YR.to_numpy()[d]
                    observed, expected = float(w @ event[d]), float(w @ intensity[d])
                    fitted["development_domains"].append(
                        {
                            "age_group": group["id"],
                            "sex": sex,
                            "baseline_state": state,
                            "n": int(d.sum()),
                            "deaths": int(event[d].sum()),
                            "observed_expected_event_intensity_ratio": observed / expected
                            if expected > 0
                            else None,
                            "interpretation": "Descriptive in-sample residual; no acceptance threshold or subgroup validation",
                        }
                    )
        report["models"][model] = fitted
    report["structural_comparison"] = {
        "interpretation": "Development sensitivity to age form; no model selection or clinical acceptance",
        "glycemic_log_hazard_changes": {
            state: report["models"]["glycemic_piecewise"]["coefficients"][i]
            - report["models"]["glycemic"]["coefficients"][i]
            for state, i in (("prediabetes", 3), ("diabetes_any_type", 4))
        },
        "likelihood_gain_over_same_age_null": {
            form: report["models"]["glycemic" + suffix]["weighted_mean_log_likelihood"]
            - report["models"]["null" + suffix]["weighted_mean_log_likelihood"]
            for form, suffix in (("single_slope", ""), ("piecewise", "_piecewise"))
        },
    }
    return report
