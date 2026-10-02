"""Synthetic semantic audits independent of the preserved empirical report.

These fixtures deliberately forge an empirical envelope around synthetic singleton
paths and copied public aggregate source pins. This exercises the real registry
binding and verifier's semantic rejection after refreshing the outer checksums.
The fixtures are never scientific artifacts or evidence of participant acquisition.
No raw data, source cache or empirical working result is read.
"""

import copy
import hashlib
import json
from pathlib import Path
from runpy import run_path

import pytest
import yaml

from demeter.analysis import ipop_a1c as a1c
from demeter.analysis import laboratory_panel as lab
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
ASSESS = run_path(str(ROOT / "scripts/verify_ipop_a1c_working_fit.py"))["assess"]
PUBLIC_CONTRACTS = (
    "ipop-a1c-working-fit-protocol-v1.json",
    "ipop-a1c-numerical-amendment-v1.json",
    "ipop-preflight-namespace-result-v2.json",
)


@pytest.fixture
def unavailable_report(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Synthetic aggregate audit must not acquire or replay participant records")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr(a1c, "analyze_cache", forbidden)
    protocol = a1c.load_protocol()
    prior = json.loads((ROOT / "docs/validation" / PUBLIC_CONTRACTS[2]).read_bytes())
    source_pins = copy.deepcopy(prior["provenance"]["source_bytes"])
    paths = {
        "calibration": (lab.PanelPath((0.0,), (0,)),),
        "evaluation": (lab.PanelPath((0.0,), (1,)),),
    }
    coverage = {
        "full_source_structure": {"synthetic_fixture_only": True},
        "full_source_linkage": {"synthetic_fixture_only": True},
        "full_namespace_consistency": {"synthetic_fixture_only": True},
        "denominator_admitted_rows": 2,
        "admitted_row_partition": {
            key: 2 if key == "eligible_assay_day" else 0 for key in a1c.ROW_KINDS
        },
        "admitted_assay_token_categories": {"finite": 2},
        "eligible_band_counts": [1, 1, 0],
        "denominator_admitted_labels": 2,
        "partitions": {
            name: {
                "admitted_labels": 1,
                "eligible_rows": 1,
                "label_partition": {
                    key: 1 if key == "one_observation" else 0 for key in a1c.LABEL_KINDS
                },
            }
            for name in ("calibration", "evaluation")
        },
        "coordinate_values_or_individual_paths_exported": False,
        "participant_identity_verified": False,
        "assay_units_rawness_specimen_clock_verified": False,
    }
    # Replace only source preparation. The actual builder, frozen controls and
    # 200-draw bootstrap run on the two synthetic paths without any estimator fit.
    monkeypatch.setattr(a1c, "_prepare", lambda *args, **kwargs: (paths, coverage, source_pins))
    report = a1c.analyze_bytes(b"", b"", protocol=protocol, validation_only=False)
    assert report["analysis_completed"] is True, report["failure_stage"]
    assert all(
        report["models"][name]["fit_performed"] is False
        for name in ("adjacent", "unrestricted", "iid")
    )
    # Deliberately forge the acquisition envelope solely to reach offline semantic
    # checks. These assertions do not describe a real acquisition or empirical run.
    report["provenance"]["acquisition_receipts_verified"] = True
    report["provenance"]["registry_sha256"] = EvidenceRegistry.from_yaml(
        ROOT / "evidence/parameters.yaml"
    ).content_hash
    report["acquisition_audit"] = {
        "passed": True,
        "receipt_saved": True,
        "provenance": {"synthetic_fixture_only": True},
    }
    return report


def _fixture_root(tmp_path, report):
    for name in PUBLIC_CONTRACTS:
        target = tmp_path / "docs/validation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / "docs/validation" / name).read_bytes())
    registry = yaml.safe_load((ROOT / "evidence/parameters.yaml").read_text(encoding="utf-8"))
    spec = registry["datasets"]["ipop_a1c_working_fit"]
    path = "docs/validation/ipop-a1c-working-result-v1.json"
    data = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    (tmp_path / path).write_bytes(data)
    spec["working_rate_parameters"]["value"] = None
    spec["working_rate_parameters"]["estimation_status"] = (
        "conditional_analysis_completed_primary_estimate_unresolved"
    )
    # Replace any existing result registration without opening its result file.
    # Refresh bindings so rejection must come from the real semantic contract.
    spec["result"] = {
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "estimated_parameters": {
            "primary_rates_per_source_day": report["models"]["adjacent"]["rates"],
            "general_rates_per_source_day": report["models"]["unrestricted"]["rates"],
            "iid_followup_band_probabilities": report["models"]["iid"]["probabilities"],
        },
    }
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence/parameters.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    return tmp_path


def test_complete_unavailable_builder_report_passes_offline(tmp_path, unavailable_report):
    proof = ASSESS(_fixture_root(tmp_path, unavailable_report))
    assert proof["passed"] is True
    assert proof["actual_source_replay"] is None
    assert proof["clinical_acceptance_established"] is False
    assert proof["engine_activation_allowed"] is False
    assert all(check["fit_available"] is False for check in proof["fit_checks"].values())
    joint = unavailable_report["joint_uncertainty"]
    assert joint["repetitions_attempted"] == 200
    assert joint["dispositions"]["failed_primary_fits"] == 200
    assert joint["joint_rate_summary"]["available"] is False


@pytest.mark.parametrize(
    ("attack", "error"),
    (
        ("nested_scope", "Nested working analysis scope drift"),
        ("unavailable_success", "Unavailable fit must retain null estimates"),
        ("frozen_bindings", "Frozen provenance or conditioning drift"),
    ),
)
def test_rehashed_synthetic_attacks_reject_independently(
    tmp_path, unavailable_report, attack, error
):
    report = copy.deepcopy(unavailable_report)
    if attack == "nested_scope":
        report["models"]["adjacent"].update(
            clinical_fit_performed=True, engine_activation_allowed=True
        )
    elif attack == "unavailable_success":
        report["models"]["adjacent"]["log_likelihood"] = {"value": -1.0, "status": "finite"}
        report["models"]["adjacent"]["identification"] = {
            "available": True,
            "full_column_rank_at_point": True,
        }
        report["internal_evaluation"]["scores"]["adjacent"] = {
            "performed": True,
            "mean_log_score": -1.0,
        }
    else:
        report["provenance"].update(
            binding_v2_protocol_sha256="0" * 64,
            supplied_protocol_canonical_sha256="0" * 64,
            assumptions={"clinical_diagnosis": True},
        )
    with pytest.raises(ValueError, match=error):
        ASSESS(_fixture_root(tmp_path, report))
