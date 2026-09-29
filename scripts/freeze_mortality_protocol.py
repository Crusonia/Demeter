"""One-time pre-outcome registration for RFC-55; refuses replacement or late freezing."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from textwrap import indent

import yaml

from demeter.analysis.mortality_validation import PROTOCOL, STORE
from demeter.data.ingest import digest
from demeter.data.linked_mortality import COLUMNS
from demeter.schema import EvidenceRegistry


def freeze(root: Path) -> str:
    if (root / PROTOCOL).exists() or (root / STORE).exists():
        raise ValueError(
            "Protocol or reserved data already exists; do not overwrite preregistration"
        )
    registry_path = root / "evidence/parameters.yaml"
    registry = EvidenceRegistry.from_yaml(registry_path)
    development = json.loads(
        (root / "docs/validation/issue-1-mortality-development.json").read_bytes()
    )
    models = {
        name: {
            key: row[key]
            for key in ("coefficient_keys", "coefficients", "covariance", "degrees_of_freedom")
        }
        for name, row in development["models"].items()
    }
    for row in models.values():
        for key, value in zip(row["coefficient_keys"], row["coefficients"], strict=True):
            if registry.parameters[key].value != value:
                raise ValueError("Development receipt and registry disagree")
    old_sources = json.loads(
        (root / "data/sources/nhanes-mortality/2011-2012/manifest.json").read_bytes()
    )
    sources = {}
    for name, receipt in old_sources["sources"].items():
        new_name = name.replace("_G.", "_H.").replace("2011_2012", "2013_2014")
        sources[new_name] = {
            key: receipt[key]
            .replace("/2011/", "/2013/")
            .replace("2011-2012", "2013-2014")
            .replace("2011_2012", "2013_2014")
            .replace("_G.", "_H.")
            for key in (
                "url",
                "publisher",
                "title",
                "vintage",
                "format",
                "documentation",
                "use_terms",
            )
        }
    protected = [
        "src/demeter/analysis/mortality_development.py",
        "src/demeter/analysis/mortality_validation.py",
        "src/demeter/data/nhanes.py",
        "src/demeter/data/linked_mortality.py",
        "scripts/validate_mortality_holdout.py",
        "docs/validation/issue-1-mortality-development.json",
        "docs/rfcs/RFC-55-mortality-holdout.md",
    ]
    protocol = {
        "schema_version": 1,
        "protocol_id": "RFC-55-v1",
        "status": "frozen_before_reserved_outcome_retrieval",
        "development_base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "development_cycle": "2011-2012",
        "validation_cycle": "2013-2014",
        "mortality_release": "2019 public-use release, May 2022",
        "sources": sources,
        "columns": {name.replace("_G.", "_H."): columns for name, columns in COLUMNS.items()},
        "mortality_file": "NHANES_2013_2014_MORT_2019_PUBLIC.dat",
        "development_specification": registry.datasets["mortality_development"],
        "glycemic_analysis": registry.datasets["nhanes_glycemic_prevalence"]["analysis"],
        "models": models,
        "parameter_contract": {
            key: registry.parameters[key].model_dump(mode="json")
            for row in models.values()
            for key in row["coefficient_keys"]
        },
        "comparisons": [
            ["glycemic", "null"],
            ["glycemic_piecewise", "null_piecewise"],
            ["glycemic_piecewise", "glycemic"],
            ["null_piecewise", "null"],
        ],
        "protected_files": {path: digest((root / path).read_bytes()) for path in protected},
        "uncertainty_scope": "Pointwise survey-design uncertainty conditional on all four frozen fitted models. No coefficient resampling, multiplicity-adjusted superiority claim, clinical pass tolerance or total-uncertainty claim.",
        "limitations": [
            "Baseline-category prediction does not identify causal current-state mortality, progression, reversal or dietary effects.",
            "Complete-case/linkage selection remains unadjusted; original fasting weights do not establish absence of selection bias.",
            "Public examination follow-up may be perturbed and differs between cycles; integrated at-risk intensity is not a common-horizon probability.",
            "Measured glucose laboratory/method changed between cycles; no outcome-selected correction is applied.",
            "Adults below the public age top-code only; all-type diabetes is not T2D and normoglycemia is not overall metabolic health.",
            "Sparse-domain diagnostics and pointwise intervals do not establish clinical equivalence or acceptance.",
            "No validation outcome is used for fitting or selecting an age form. Later model revisions require a new validation plan.",
            "External expert review pending; full scientific v0.1 acceptance remains unresolved.",
        ],
    }
    content = (json.dumps(protocol, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    (root / PROTOCOL).write_bytes(content)
    sha = digest(content)
    spec = {
        "mortality_validation": {
            "status": "derived",
            "evidence_grade": "C",
            "model_role": "prediction_benchmark_only",
            "protocol": PROTOCOL.as_posix(),
            "protocol_sha256": sha,
            "rfc": "docs/rfcs/RFC-55-mortality-holdout.md",
            "development_cycle": "2011-2012",
            "validation_cycle": "2013-2014",
            "mortality_release": "2019 public-use",
            "source_store": STORE.as_posix(),
            "population": "Complete adult fasting baseline below age top-code, linked, with positive examination follow-up; frozen RFC-1 domain",
            "geography": "United States",
            "unit": "Censored log score, integrated event intensity, observed/expected ratio, record counts",
            "numerical_controls": "Frozen existing mortality_development and nhanes_glycemic_prevalence.analysis; no new numerical calibration or thresholds",
            "uncertainty": protocol["uncertainty_scope"],
            "transformation": "demeter.analysis.mortality_validation.validation_report",
        }
    }
    text = registry_path.read_text(encoding="utf-8")
    if "mortality_validation" in registry.datasets or text.count("\ndatasets:\n") != 1:
        raise ValueError("Unexpected registry layout or existing validation dataset")
    text = text.replace(
        "\ndatasets:\n",
        "\ndatasets:\n" + indent(yaml.safe_dump(spec, sort_keys=False, width=100), "  "),
        1,
    )
    registry_path.write_text(text, encoding="utf-8", newline="\n")
    packages_path = root / "data/evidence-packages.json"
    packages = json.loads(packages_path.read_bytes())
    packages["supporting_artifacts"].append({"path": PROTOCOL.as_posix(), "sha256": sha})
    packages["packages"]["mortality_validation"] = {
        "store": None,
        "dependencies": ["mortality_development"],
        "registry_datasets": ["mortality_validation"],
        "registry_parameters": [],
        "artifacts": [],
        "transform_files": [
            "src/demeter/analysis/mortality_validation.py",
            "scripts/validate_mortality_holdout.py",
        ],
        "rebuild": ["uv run python scripts/validate_mortality_holdout.py"],
        "model_role": "prediction_benchmark_only",
        "redistribution": "Frozen Demeter protocol and aggregate diagnostics with source terms retained; no joined individual-level exports.",
    }
    packages_path.write_text(json.dumps(packages, indent=2) + "\n", encoding="utf-8", newline="\n")
    return sha


if __name__ == "__main__":
    print(freeze(Path(__file__).resolve().parents[1]))
