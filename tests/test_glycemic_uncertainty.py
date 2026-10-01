"""Synthetic validation and unchanged archived benchmark comparisons; no clinical fit."""

import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from demeter.data import glycemic_uncertainty as module
from demeter.data import nhanes
from demeter.data.ingest import digest
from demeter.data.partial_observations import possible_categories
from demeter.schema import EvidenceRegistry


@pytest.fixture
def registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


@pytest.fixture
def frame():
    """Arbitrary software-only observations with exclusions and unresolved categories."""
    common = {"RIDEXPRG": np.nan, "DIQ010": 2, "LBXGH": 5.0, "LBXGLU": 90.0}
    cases = [
        {"RIAGENDR": 1, "RIDAGEYR": 40},
        {"RIAGENDR": 2, "RIDAGEYR": 40, "LBXGH": 6.0},
        {"RIAGENDR": 1, "RIDAGEYR": 70, "DIQ010": 1, "LBXGH": np.nan},
        {"RIAGENDR": 2, "RIDAGEYR": 60, "DIQ010": 9},
        {"RIAGENDR": 1, "RIDAGEYR": 25, "LBXGLU": np.nan},
        {"RIAGENDR": 2, "RIDAGEYR": 35, "RIDEXPRG": 1},
        {"RIAGENDR": 1, "RIDAGEYR": 10},
        {"RIAGENDR": 2, "RIDAGEYR": 70, "LBXGLU": np.nan, "LBXGH": 6.0},
    ]
    return pd.DataFrame(
        [
            common
            | case
            | {
                "WTSAFPRP": float(i + 1),
                "SDMVSTRA": i // 4 + 1,
                "SDMVPSU": (i // 2) % 2 + 1,
                "SEQN": 90000 + i,
            }
            for i, case in enumerate(cases)
        ],
        index=[f"PRIVATE_SYNTHETIC_ROW_{i}" for i in range(len(cases))],
    )


def coordinate_index(result, domain, membership):
    return result["coordinates"].index({"domain": domain, "membership": membership})


def test_fixed_partitions_include_zero_patterns_and_retain_history(frame, registry):
    report = module.assess(frame, registry)
    sample, domains, memberships, definitions, _, _ = module._observations(frame, registry)
    complete = memberships.filter(regex="^complete:")
    partial = memberships.filter(regex="^partial:")
    assert complete.shape[1] == 4
    assert partial.shape[1] == 7
    assert complete.sum(axis=1).eq(1).all()
    assert partial.sum(axis=1).eq(1).all()
    assert list(partial.columns) == ["partial:" + "|".join(p) for p in module.PARTIAL_PATTERNS]
    # An unrealized compatible subset remains an explicit zero coordinate.
    assert not memberships["partial:normoglycemia|prediabetes"].any()
    # Reported diagnosis with an absent lab remains unclassified in the unchanged
    # complete definition and definite diabetes in the existing partial helper.
    assert memberships.loc[frame.index[2], "complete:unclassified"]
    assert memberships.loc[frame.index[2], "partial:diabetes_any_type"]
    assert report["counts"] == {
        "source_n": 8,
        "positive_weight_n": 8,
        "under_adult_minimum_n": 1,
        "known_pregnancy_n": 1,
        "eligible_n": 6,
    }
    assert len(sample) == len(frame)  # Excluded people still retain full-design PSUs.
    assert not domains.loc[frame.index[5:7]].any(axis=None)
    assert len(definitions) == 11
    serialized = json.dumps(report)
    assert "SEQN" not in serialized
    assert "PRIVATE_SYNTHETIC_ROW" not in serialized
    assert "90000" not in serialized
    assert not report["direct_initialization_allowed"]
    assert not report["clinical_fit_allowed"]
    assert not report["engine_activation_allowed"]
    assert not report["sampling_distribution_assumed"]
    assert not report["scientific_release_ready"]


def test_every_joint_point_and_diagonal_matches_unchanged_scalar(frame, registry):
    sample, domains, memberships, _, _, _ = module._observations(frame, registry)
    report = module.assess(frame, registry)
    joint = report["joint"]
    confidence = nhanes.definition(registry)["analysis"]["confidence_level"]
    for i, coordinate in enumerate(joint["coordinates"]):
        scalar = nhanes.survey_proportion(
            sample, domains[coordinate["domain"]], memberships[coordinate["membership"]], confidence
        )
        if scalar["estimate"] is None:
            assert joint["estimates"][i] is None
            assert all(v is None for v in joint["covariance"][i])
        else:
            assert joint["estimates"][i] == pytest.approx(scalar["estimate"], abs=1e-14)
            assert joint["covariance"][i][i] == pytest.approx(
                scalar["standard_error"] ** 2, abs=1e-14
            )


def test_full_bound_projection_matches_direct_binary_and_covariance(frame, registry):
    sample, domains, _, _, _, _ = module._observations(frame, registry)
    report = module.assess(frame, registry)
    possible = possible_categories(sample, registry, "glycemic")
    confidence = nhanes.definition(registry)["analysis"]["confidence_level"]
    projected = report["bound_endpoints"]
    joint = report["joint"]
    for i, coordinate in enumerate(projected["coordinates"]):
        outcome = possible[coordinate["category"]].copy()
        if coordinate["endpoint"] == "lower":
            outcome &= possible.sum(axis=1) == 1
        scalar = nhanes.survey_proportion(
            sample, domains[coordinate["domain"]], outcome, confidence
        )
        if scalar["estimate"] is None:
            assert projected["estimates"][i] is None
            assert all(v is None for v in projected["covariance"][i])
        else:
            assert projected["estimates"][i] == pytest.approx(scalar["estimate"], abs=1e-14)
            assert projected["covariance"][i][i] == pytest.approx(
                scalar["standard_error"] ** 2, abs=1e-14
            )
    available = np.array([value is not None for value in joint["estimates"]])
    bound_available = np.array([value is not None for value in projected["estimates"]])
    matrix = np.asarray(projected["projection"])[:, available][bound_available]
    covariance = np.asarray(joint["covariance"], dtype=float)[np.ix_(available, available)]
    expected = matrix @ covariance @ matrix.T
    actual = np.asarray(projected["covariance"], dtype=float)[
        np.ix_(bound_available, bound_available)
    ]
    assert actual == pytest.approx(expected, abs=1e-14)


def test_dependence_closure_and_singular_covariance_are_preserved(frame, registry):
    report = module.assess(frame, registry)
    joint = report["joint"]
    available = np.array([p is not None for p in joint["estimates"]])
    covariance = np.asarray(joint["covariance"], dtype=float)[np.ix_(available, available)]
    assert covariance == pytest.approx(covariance.T, abs=1e-14)
    assert np.linalg.eigvalsh(covariance).min() >= -1e-12
    assert np.linalg.matrix_rank(covariance) < len(covariance)
    for constraint in report["diagnostics"]["partition_constraints"]:
        if constraint["available"]:
            indices = [
                i
                for i, coordinate in enumerate(joint["coordinates"])
                if coordinate["domain"] == constraint["domain"]
                and coordinate["membership"].startswith(constraint["partition"] + ":")
            ]
            assert sum(joint["estimates"][i] for i in indices) == pytest.approx(1, abs=1e-14)
            for j in np.flatnonzero(available):
                assert sum(joint["covariance"][i][j] for i in indices) == pytest.approx(
                    0, abs=1e-14
                )
    assert not report["diagnostics"]["matrix_repair_performed"]
    domain = report["domain_definitions"][0]["domain"]
    complete = coordinate_index(joint, domain, "complete:normoglycemia")
    partial = coordinate_index(joint, domain, "partial:normoglycemia")
    assert joint["covariance"][complete][partial] != 0
    male = coordinate_index(joint, domain.replace(":all", ":male"), "complete:normoglycemia")
    assert joint["covariance"][complete][male] != 0


def test_weight_scale_and_row_order_do_not_change_joint_result(frame, registry):
    original = module.assess(frame, registry)
    scaled = frame.copy()
    scaled.WTSAFPRP *= 1e100
    changed = module.assess(scaled.iloc[::-1], registry)
    for key in ("joint", "bound_endpoints"):
        assert changed[key]["coordinates"] == original[key]["coordinates"]
        for before, after in zip(
            original[key]["estimates"], changed[key]["estimates"], strict=True
        ):
            assert after is None if before is None else after == pytest.approx(before, abs=1e-14)
        available = np.array([p is not None for p in original[key]["estimates"]])
        before = np.asarray(original[key]["covariance"], dtype=float)[np.ix_(available, available)]
        after = np.asarray(changed[key]["covariance"], dtype=float)[np.ix_(available, available)]
        assert after == pytest.approx(before, abs=1e-14)


@pytest.mark.parametrize(
    "key,value",
    [
        ("model_role", "initialization"),
        ("method", "independent_draws"),
        ("direct_initialization_allowed", True),
        ("direct_initialization_allowed", 0),
        ("clinical_fit_allowed", True),
        ("engine_activation_allowed", True),
        ("sampling_distribution_assumed", True),
    ],
)
def test_scope_drift_rejects_before_calculation(frame, registry, monkeypatch, key, value):
    registry.datasets[module.DATASET][key] = value
    monkeypatch.setattr(module.survey_joint, "joint_proportions", lambda *args: pytest.fail("math"))
    with pytest.raises(ValueError, match="benchmark-only"):
        module.assess(frame, registry)


@pytest.mark.parametrize(
    "column,value",
    [
        ("WTSAFPRP", -1),
        ("WTSAFPRP", np.inf),
        ("RIDAGEYR", np.nan),
        ("RIDAGEYR", 81),
        ("RIAGENDR", 9),
    ],
)
def test_invalid_public_observation_coding_rejects(frame, registry, column, value):
    frame.loc[frame.index[0], column] = value
    with pytest.raises(ValueError):
        module.assess(frame, registry)


def test_duplicate_index_and_singleton_full_design_reject(frame, registry):
    duplicate = frame.copy()
    duplicate.index = ["duplicate"] * len(frame)
    with pytest.raises(ValueError, match="coding"):
        module.assess(duplicate, registry)
    frame.SDMVPSU = 1
    with pytest.raises(ValueError, match="Singleton"):
        module.assess(frame, registry)


def test_all_empty_domains_remain_unavailable(frame, registry):
    frame.RIDAGEYR = 10
    report = module.assess(frame, registry)
    assert all(value is None for value in report["joint"]["estimates"])
    assert all(value is None for value in report["bound_endpoints"]["estimates"])
    assert report["diagnostics"]["available_coordinates"] == 0
    assert report["diagnostics"]["available_domains"] == 0


def test_frozen_guards_reject_before_source_parse_or_analysis(registry, monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("No source parse or analysis may precede frozen checks")

    monkeypatch.setattr(module.nhanes, "read_store", forbidden)
    monkeypatch.setattr(module, "assess", forbidden)
    registry.datasets["observation_state_mapping"]["topcoded_age"] += 1
    with pytest.raises(ValueError, match="definition checksum"):
        module.joint_report(registry)


def test_coordinated_protocol_repin_still_rejects(registry, monkeypatch, tmp_path):
    content = json.loads(module.PROTOCOL_PATH.read_bytes())
    content["clinical_activation_allowed"] = True
    replacement = tmp_path / "protocol.json"
    replacement.write_bytes(nhanes.encoded(content))
    monkeypatch.setattr(module, "PROTOCOL_PATH", replacement)
    registry.datasets[module.DATASET]["protocol_path"] = str(replacement)
    registry.datasets[module.DATASET]["protocol_sha256"] = digest(replacement.read_bytes())
    monkeypatch.setattr(module.nhanes, "read_store", lambda *args: pytest.fail("source parse"))
    with pytest.raises(ValueError, match="identity mismatch"):
        module.joint_report(registry)


def test_protocol_file_and_original_implementation_tamper_reject(registry, monkeypatch):
    original = Path.read_bytes

    def corrupt(path):
        content = original(path)
        if path == module.PROTOCOL_PATH:
            return content + b" "
        return content

    monkeypatch.setattr(Path, "read_bytes", corrupt)
    with pytest.raises(ValueError, match="protocol checksum"):
        module.joint_report(registry)
    monkeypatch.setattr(Path, "read_bytes", original)

    def corrupt_implementation(path):
        content = original(path)
        if path.as_posix() == "src/demeter/data/nhanes.py":
            return content + b"# drift"
        return content

    monkeypatch.setattr(Path, "read_bytes", corrupt_implementation)
    with pytest.raises(ValueError, match="artifact checksum"):
        module.joint_report(registry)


def test_custom_source_forged_manifest_rejects_before_parsing(registry, monkeypatch, tmp_path):
    source = tmp_path / "custom-store"
    source.mkdir()
    manifest = json.loads((nhanes.STORE / "manifest.json").read_bytes())
    manifest["sources"]["P_GLU.xpt"]["sha256"] = "0" * 64
    (source / "manifest.json").write_bytes(nhanes.encoded(manifest))
    monkeypatch.setattr(module.nhanes, "read_store", lambda *args: pytest.fail("source parse"))
    with pytest.raises(ValueError, match="artifact checksum"):
        module.joint_report(registry, source)


def test_four_source_checksums_precede_any_xpt_parse(registry, monkeypatch, tmp_path):
    source = tmp_path / "checksummed-copy"
    source.mkdir()
    for name in ("manifest.json", *nhanes.COLUMNS):
        shutil.copyfile(nhanes.STORE / name, source / name)
    # Corrupt the final source in the manifest order; parsing any earlier valid
    # source must still be prohibited until all four byte checks have passed.
    with (source / "P_GLU.xpt").open("ab") as stream:
        stream.write(b"synthetic checksum drift")
    monkeypatch.setattr(module.nhanes, "read_xpt", lambda *args: pytest.fail("premature parse"))
    monkeypatch.setattr(module, "assess", lambda *args: pytest.fail("premature math"))
    with pytest.raises(ValueError, match="source checksum mismatch: P_GLU.xpt"):
        module.joint_report(registry, source)


def test_real_offline_points_bounds_and_se_match_saved_reports(registry, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args: pytest.fail("offline only"))
    original_files = {
        name: digest(Path(name).read_bytes())
        for name in json.loads(module.PROTOCOL_PATH.read_bytes())["existing_artifact_sha256"]
    }
    report = module.joint_report(registry)
    complete = json.loads(Path("docs/validation/issue-56-state-mapping.json").read_bytes())
    partial = json.loads(Path("docs/validation/issue-56-partial-observations.json").read_bytes())
    complete_domains = next(d for d in complete["definitions"] if d["id"] == "glycemic")["domains"]
    partial_domains = next(d for d in partial["definitions"] if d["id"] == "glycemic")["domains"]
    for domain, previous, previous_partial in zip(
        report["domain_definitions"], complete_domains, partial_domains, strict=True
    ):
        assert (domain["age_group"], domain["sex"]) == (previous["age_group"], previous["sex"])
        for name in module.COMPLETE_LABELS:
            index = coordinate_index(report["joint"], domain["domain"], f"complete:{name}")
            old = previous["categories"][name]["eligible_weight_proportion"]
            assert report["joint"]["estimates"][index] == pytest.approx(
                old["estimate"], rel=1e-10, abs=1e-14
            )
            assert report["joint"]["covariance"][index][index] == pytest.approx(
                old["standard_error"] ** 2, rel=1e-10, abs=1e-14
            )
        for name in nhanes.STATES:
            for endpoint in ("lower", "upper"):
                index = report["bound_endpoints"]["coordinates"].index(
                    {"domain": domain["domain"], "category": name, "endpoint": endpoint}
                )
                old = previous_partial["categories"][name]["endpoint_sampling"][endpoint]
                assert report["bound_endpoints"]["estimates"][index] == pytest.approx(
                    old["estimate"], rel=1e-10, abs=1e-14
                )
                assert report["bound_endpoints"]["covariance"][index][index] == pytest.approx(
                    old["standard_error"] ** 2, rel=1e-10, abs=1e-14
                )
    assert report["source_audit_passed"]
    assert report["provenance"]["protocol_sha256"] == module.PROTOCOL_SHA256
    assert set(report["provenance"]["source_sha256"]) == set(nhanes.COLUMNS)
    assert report["provenance"]["used_source"] is True
    assert "SEQN" not in json.dumps(report)
    assert nhanes.encoded(report).endswith(b"\n")
    assert b"\r\n" not in nhanes.encoded(report)
    assert {name: digest(Path(name).read_bytes()) for name in original_files} == original_files
