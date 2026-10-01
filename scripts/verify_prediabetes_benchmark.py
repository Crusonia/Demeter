"""Check the registered CDC prediabetes interval against its archived PDF, offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
STORE = Path("data/sources/cdc-prediabetes/2026-10-01")
KEY = "observed_prediabetes_65_plus"


def extract_interval(text: str) -> tuple[float, float, float]:
    """Select the first column of the ≥65 row, rejecting ambiguous table matches."""
    normalized = " ".join(text.split())
    for heading in (
        "Estimated Crude Percentage of Prediabetes and Awareness",
        "Adults Aged 18 Years or Older, United States, 2021–2023",
        "Percentage (95% CI)",
        "Age Group",
        "Prediabetes Awareness",
    ):
        if heading not in normalized:
            raise ValueError("CDC crude prediabetes table heading missing")
    pattern = (
        r"^\s*≥65\s+(\d+\.\d+)\s*\((\d+\.\d+)[–-](\d+\.\d+)\)"
        r"\s+\d+\.\d+\s*\(\d+\.\d+[–-]\d+\.\d+\)\s*$"
    )
    rows = re.findall(pattern, text, re.MULTILINE)
    if len(rows) != 1:
        raise ValueError("Expected exactly one CDC ≥65 row with both table columns")
    values = tuple(float(Decimal(value) / Decimal(100)) for value in rows[0])
    if not 0 <= values[1] <= values[0] <= values[2] <= 1:
        raise ValueError("Invalid published prediabetes interval")
    return values


def verify_benchmark(root: Path = ROOT) -> dict:
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    manifest = json.loads((root / STORE / "manifest.json").read_bytes())
    spec = manifest["extraction"]
    receipt = manifest["sources"][spec["filename"]]
    path = root / STORE / spec["filename"]
    if (
        manifest["schema_version"] != 1
        or spec["registry_key"] != KEY
        or receipt["model_role"] != "benchmark_only"
    ):
        raise ValueError("Invalid CDC benchmark manifest identity or role")
    content = path.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    if sha != receipt["sha256"] or len(content) != receipt["bytes"]:
        raise ValueError("CDC prediabetes source bytes differ from the pinned receipt")
    reader = PdfReader(path)
    values = extract_interval(
        reader.pages[spec["pdf_page_index"]].extract_text(extraction_mode="layout")
    )
    parameter = registry.parameters[KEY]
    interval = parameter.uncertainty
    if (
        parameter.model_role != "benchmark_only"
        or parameter.status != "observed"
        or parameter.unit != "fraction"
        or parameter.source_url != receipt["url"]
        or interval is None
        or interval.kind != "interval"
        or values != (parameter.value, interval.low, interval.high)
    ):
        raise ValueError("CDC published interval does not match the registered benchmark")
    return {
        "passed": True,
        "network_used": False,
        "scientific_release_ready": False,
        "model_role": "benchmark_only",
        "registry_key": KEY,
        "evidence_sha256": registry.content_hash,
        "source": receipt,
        "source_locator": spec["locator"],
        "transformation": "First estimate/95% CI of the ≥65 row, divided by 100; no re-estimation",
        "value": values[0],
        "uncertainty": {"kind": "interval", "low": values[1], "high": values[2]},
        "interpretation": "Published crude prevalence interval only; not IR calibration, "
        "a sampling distribution, transition rates or causal dietary evidence.",
    }


def compare_registries(previous: Path, root: Path = ROOT) -> dict:
    """Compare full outputs with only the two declared evidence-hash paths omitted."""
    from demeter.analysis.experiments import sampled_parameters, uncertainty
    from demeter.analysis.validation import mortality_backtest, prevalence_checks, validate
    from demeter.model import simulate
    from demeter.schema import Scenario

    old = EvidenceRegistry.from_yaml(previous)
    new = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")

    def normalized(result):
        result["metadata"].pop("evidence_sha256")
        if result.get("healthspan") is not None:
            result["healthspan"].pop("evidence_sha256")
        return result

    checks = []
    for name in ("baseline", "reduce_upf_30", "prechronic_baseline", "prechronic_reduce_upf_30"):
        scenario = Scenario.from_yaml(root / "scenarios" / f"{name}.yaml")
        before = normalized(simulate(old, scenario).to_dict())
        after = normalized(simulate(new, scenario).to_dict())
        checks.append(
            {
                "scenario": name,
                "complete_outputs_equal_except_evidence_hash": before == after,
                "absolute_numeric_change": 0 if before == after else None,
                "relative_numeric_change": 0 if before == after else None,
            }
        )
    scenario = Scenario.from_yaml(root / "scenarios/reduce_upf_30.yaml").model_copy(
        update={"years": 2}
    )
    before_u = normalized(uncertainty(old, scenario, draws=2, seed=42, diagnostics=True))
    after_u = normalized(uncertainty(new, scenario, draws=2, seed=42, diagnostics=True))
    readiness = validate(new)
    report = {
        "before_evidence_sha256": old.content_hash,
        "after_evidence_sha256": new.content_hash,
        "excluded_paths": ["/metadata/evidence_sha256", "/healthspan/evidence_sha256"],
        "canonical_scenarios": checks,
        "sampling_inputs_unchanged": sampled_parameters(old, scenario)
        == sampled_parameters(new, scenario),
        "benchmark_not_sampled": KEY not in sampled_parameters(new, scenario),
        "fixed_seed_uncertainty_unchanged": before_u == after_u,
        "uncertainty_check": {
            "seed": 42,
            "draws": 2,
            "years": 2,
            "scope": "Software regression with synthetic active parameters",
        },
        "prevalence_checks_unchanged": prevalence_checks(old) == prevalence_checks(new),
        "mortality_backtest_unchanged": mortality_backtest() == readiness["historical_backtest"],
        "scientific_blockers_unchanged": old.scientific_blockers == new.scientific_blockers,
        "before_missing_uncertainty": old.audit()["missing_uncertainty"],
        "after_missing_uncertainty": new.audit()["missing_uncertainty"],
        "scientific_release_ready": readiness["scientific_release_ready"],
        "interpretation": "Benchmark metadata correction; no clinical validation or model calibration",
    }
    report["passed"] = (
        all(check["complete_outputs_equal_except_evidence_hash"] for check in checks)
        and all(
            report[key]
            for key in (
                "sampling_inputs_unchanged",
                "benchmark_not_sampled",
                "fixed_seed_uncertainty_unchanged",
                "prevalence_checks_unchanged",
                "mortality_backtest_unchanged",
                "scientific_blockers_unchanged",
            )
        )
        and not report["scientific_release_ready"]
    )
    if not report["passed"]:
        raise ValueError(
            "Benchmark correction changed an undeclared model result or scientific gate"
        )
    return report


def write_report(report: dict, output: Path) -> None:
    """Create a new result exclusively; never overwrite an input or alias."""
    content = json.dumps(report, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    except FileExistsError as exc:
        raise ValueError(
            "Output must be a new file; existing files and aliases are preserved"
        ) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    parser.add_argument(
        "--output", type=Path, default=Path(f"outputs/cdc-prediabetes-benchmark-{stamp}.json")
    )
    parser.add_argument(
        "--previous-registry", type=Path, help="Also reproduce a before/after check"
    )
    args = parser.parse_args()
    report = verify_benchmark()
    if args.previous_registry is not None:
        report["before_after"] = compare_registries(args.previous_registry)
    write_report(report, args.output)
    print(
        json.dumps({key: report[key] for key in ("passed", "model_role", "value", "uncertainty")})
    )
