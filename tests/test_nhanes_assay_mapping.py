"""Synthetic paired observations; these tests never parse NHANES records."""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from demeter.data import nhanes, nhanes_assay_mapping as mapping
from demeter.data import nhanes_current_store as store
from demeter.schema import EvidenceRegistry


@pytest.fixture
def registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml").model_copy(deep=True)


def frame():
    return pd.DataFrame(
        {
            "SEQN": range(99110001, 99110009),
            "WTSAF2YR": [1.0, 2.0, 1.0, 3.0, 2.0, 1.0, 1.0, 2.0],
            "SDDSRVYR": [12] * 8,
            "RIDSTATR": [2] * 8,
            "RIDAGEYR": [25, 25, 45, 45, 65, 65, 17, 80],
            "RIAGENDR": [1, 2, 1, 2, 1, 2, 1, 2],
            "RIDEXPRG": [np.nan, 2, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
            "DIQ010": [2, 1, 2, 3, 1, 9, 2, 2],
            "LBXGH": [5.0, 5.0, 5.7, 6.5, np.nan, 5.0, 5.0, 5.0],
            "LBXGLU": [100.0, 90.0, 90.0, 126.0, 90.0, 90.0, 90.0, 90.0],
            "SDMVSTRA": [1, 1, 1, 1, 2, 2, 2, 2],
            "SDMVPSU": [1, 2, 1, 2, 1, 2, 1, 2],
        }
    )


def private_observations(data, registry):
    spec = mapping.definition(registry)
    sample, _ = mapping.current._sample(data, spec)
    return sample, mapping._observations(sample, spec)


def coordinate(result, domain, member):
    return result["joint"]["coordinates"].index({"domain": domain, "membership": member})


@pytest.fixture(scope="module")
def result():
    return mapping.assess(frame(), EvidenceRegistry.from_yaml("evidence/parameters.yaml"))


def test_order_partition_closure_and_privacy(result, registry):
    spec = mapping.definition(registry)
    assert result["joint"]["coordinates"] == spec["coordinate_order"]
    assert len(result["joint"]["coordinates"]) == 204
    assert result["diagnostics"]["rectangular_calculation_coordinates"] == 408
    assert len(result["discordance"]["estimates"]) == 12
    assert len(result["discordance"]["covariance"]) == 12
    assert result["source_audit_passed"] is False
    assert all(result[name] is False for name in mapping.GATES)
    assert result["joint"]["design"]["positive_weight_n"] == 8
    assert result["joint"]["design"]["weight"] == "WTSAF2YR"
    assert result["joint"]["design"]["internal_working_weight"] == "WTSAFPRP"
    text = nhanes.encoded(result).decode()
    assert "99110001" not in text and "SEQN" not in text
    assert "LBXGH" not in text and "LBXGLU" not in text
    for domain in ("eligible:20_plus:all", "eligible:40_59:all"):
        indices = [coordinate(result, domain, m) for m in spec["eligible_memberships"]]
        values = np.array(result["joint"]["estimates"])[indices]
        assert sum(values[:4]) == pytest.approx(1)
        assert sum(values[4:]) == pytest.approx(1)
        assert sum(values) == pytest.approx(2)
        cov = np.array(result["joint"]["covariance"], dtype=float)
        for partition in (indices[:4], indices[4:]):
            available = np.isfinite(cov[partition, :]).all(axis=0)
            assert cov[partition, :][:, available].sum(axis=0) == pytest.approx(
                np.zeros(int(available.sum())), abs=1e-15
            )


def test_bidirectional_disagreement_and_scalar_projection_parity(result):
    row = result["equivalence"][0]
    assert row["n"] == 3 and row["discordant_n"] == 2
    assert row["status"] == "contradicted_in_observed_sample"
    assert row["scalar"]["estimate"] == pytest.approx(0.5)
    for i, row in enumerate(result["equivalence"]):
        assert result["discordance"]["estimates"][i] == pytest.approx(row["scalar"]["estimate"])
        if row["scalar"]["standard_error"] is not None:
            assert result["discordance"]["covariance"][i][i] == pytest.approx(
                row["scalar"]["standard_error"] ** 2, abs=1e-15
            )
    forward = coordinate(
        result, "paired_no:20_plus:all", "a1c:normoglycemic_range|fpg:prediabetes_range"
    )
    backward = coordinate(
        result, "paired_no:20_plus:all", "a1c:prediabetes_range|fpg:normoglycemic_range"
    )
    assert result["joint"]["estimates"][forward] == pytest.approx(0.25)
    assert result["joint"]["estimates"][backward] == pytest.approx(0.25)


def test_hand_calculated_covariance_retains_cross_denominator_dependence(result):
    data = frame()
    weight = data.WTSAF2YR.to_numpy()
    eligible = np.array([True, True, True, True, True, True, False, True])
    paired = np.array([True, False, True, False, False, False, False, True])
    no = data.DIQ010.eq(2).to_numpy()
    forward = np.array([True, False, False, False, False, False, False, False])
    backward = np.array([False, False, True, False, False, False, False, False])
    masks = [(eligible, no), (paired, forward), (paired, backward)]
    # Independent small-fixture ratio influences and two-PSU stratum contrasts.
    influences = []
    for domain, member in masks:
        denominator = sum(weight[domain])
        mean = sum(weight[domain & member]) / denominator
        influences.append(weight * domain * (member - mean) / denominator)
    contrasts = []
    for stratum in (1, 2):
        contrasts.append(
            [
                sum(influence[data.SDMVSTRA.eq(stratum) & data.SDMVPSU.eq(1)])
                - sum(influence[data.SDMVSTRA.eq(stratum) & data.SDMVPSU.eq(2)])
                for influence in influences
            ]
        )
    expected = np.array(contrasts).T @ np.array(contrasts)
    indices = [
        coordinate(result, "eligible:20_plus:all", "diq:no"),
        coordinate(
            result, "paired_no:20_plus:all", "a1c:normoglycemic_range|fpg:prediabetes_range"
        ),
        coordinate(
            result, "paired_no:20_plus:all", "a1c:prediabetes_range|fpg:normoglycemic_range"
        ),
    ]
    observed = np.array(result["joint"]["covariance"], dtype=float)[np.ix_(indices, indices)]
    assert observed == pytest.approx(expected, abs=1e-15)
    assert expected[0, 1] != 0  # Different denominators are not independent.


def test_equal_marginals_do_not_establish_individual_equivalence(registry):
    data = frame()
    data["DIQ010"] = 2
    data["RIDAGEYR"] = 30
    data["WTSAF2YR"] = 1.0
    data["LBXGH"] = [5.0, 5.7] * 4
    data["LBXGLU"] = [100.0, 90.0] * 4
    report = mapping.assess(data, registry)
    row = report["equivalence"][0]
    assert row["discordant_n"] == row["n"] == 8
    assert row["scalar"]["estimate"] == 1
    assert row["status"] == "contradicted_in_observed_sample"
    assert row["scalar"]["interval"] is None
    # Each assay has four normal and four prediabetes range values, yet none agree.
    assert int((data.LBXGH < 5.7).sum()) == int((data.LBXGLU < 100).sum()) == 4


def test_exact_edges_and_invalid_assays_are_availability_not_clinical_states(registry):
    data = frame()
    data["DIQ010"] = 2
    data["LBXGH"] = [5.7, 6.5, np.nextafter(5.7, 0), 0, -1, np.inf, np.nan, 5.0]
    data["LBXGLU"] = [100, 126, np.nextafter(100.0, 0), 100, -1, 100, np.nan, np.inf]
    _, (_, members, _, _) = private_observations(data, registry)
    assert members.loc[0, "a1c:prediabetes_range|fpg:prediabetes_range"]
    assert members.loc[1, "a1c:diabetes_range|fpg:diabetes_range"]
    assert members.loc[2, "a1c:normoglycemic_range|fpg:normoglycemic_range"]
    assert members.loc[3, "availability:fpg_only"]
    assert members.loc[4, "availability:neither"]
    assert members.loc[5, "availability:fpg_only"]
    assert members.loc[6, "availability:neither"]
    assert members.loc[7, "availability:a1c_only"]


def test_literal_diq_groups_and_pregnancy_scope(registry):
    data = frame()
    data["DIQ010"] = [1, 2, 3, 7, 9, np.nan, 2, 2]
    data["LBXGH"] = 5.0
    data["LBXGLU"] = 90.0
    data.loc[1, "RIDEXPRG"] = 1
    data.loc[3, "RIDEXPRG"] = 1  # age45 outside released exclusion scope
    _, (domains, members, _, counts) = private_observations(data, registry)
    assert members["diq:yes"].sum() == 1
    assert members["diq:no"].sum() == 3
    assert members["diq:borderline"].sum() == 1
    assert members["diq:uninterpretable"].sum() == 3
    assert domains["paired_no:20_plus:all"].sum() == 1
    assert counts["known_pregnancy_n"] == 1
    assert counts["under_adult_minimum_n"] == 1
    assert domains.loc[3, "eligible:40_59:all"]
    assert domains.loc[7, "paired_no:60_plus:female"]


def test_empty_and_nonempty_agreement_do_not_claim_validation(registry):
    data = frame()
    data["DIQ010"] = 1
    empty = mapping.assess(data, registry)
    assert all(row["status"] == "not_evaluable" for row in empty["equivalence"])
    assert all(v is None for v in empty["discordance"]["estimates"])
    assert all(v is None for row in empty["discordance"]["covariance"] for v in row)
    data["DIQ010"] = 2
    data["LBXGH"] = 5.0
    data["LBXGLU"] = 90.0
    agreement = mapping.assess(data, registry)
    assert agreement["equivalence"][0]["status"] == "not_contradicted_in_observed_sample"
    assert agreement["equivalence"][0]["scalar"]["interval"] is None


def test_full_design_and_input_immutability(registry):
    data = frame()
    before = data.copy(deep=True)
    report = mapping.assess(data, registry)
    pd.testing.assert_frame_equal(data, before)
    assert report["counts"]["eligible_n"] == 7
    assert report["joint"]["design"]["psus"] == 4
    data.loc[data.SDMVSTRA.eq(2), "SDMVPSU"] = 1
    with pytest.raises(ValueError, match="Singleton full-design"):
        mapping.assess(data, registry)


def test_zero_contribution_psu_is_retained(registry):
    data = frame()
    data.loc[[5, 7], "RIDAGEYR"] = 17
    report = mapping.assess(data, registry)
    assert report["counts"]["eligible_n"] == 5
    assert report["joint"]["design"]["psus"] == 4
    assert report["joint"]["design"]["degrees_of_freedom"] == 2
    # Premature domain filtering removes the entire stratum2/PSU2 and must fail.
    with pytest.raises(ValueError, match="Singleton full-design"):
        mapping.assess(data.loc[data.RIDAGEYR.ge(20)], registry)


def test_weight_scaling_preserves_joint_covariance(registry, result):
    data = frame()
    data["WTSAF2YR"] *= 1000
    scaled = mapping.assess(data, registry)
    for section in ("joint", "discordance"):
        assert np.array(scaled[section]["estimates"], dtype=float) == pytest.approx(
            np.array(result[section]["estimates"], dtype=float), nan_ok=True
        )
        assert np.array(scaled[section]["covariance"], dtype=float) == pytest.approx(
            np.array(result[section]["covariance"], dtype=float), nan_ok=True, abs=1e-15
        )


@pytest.mark.parametrize("field", mapping.GATES)
def test_gate_activation_refused_before_sample(registry, field, monkeypatch):
    registry.datasets[mapping.DATASET][field] = True
    monkeypatch.setattr(mapping.current, "_sample", lambda *args: pytest.fail("sample called"))
    with pytest.raises(ValueError, match="definition"):
        mapping.assess(frame(), registry)


@pytest.mark.parametrize(
    "field",
    [
        "coordinate_order",
        "coordinate_selection_indices",
        "discordance_projection",
        "paired_memberships",
        "diq_groups",
        "analysis",
    ],
)
def test_frozen_definition_drift_refused(registry, field):
    registry.datasets[mapping.DATASET][field] = []
    with pytest.raises(ValueError, match="definition"):
        mapping.definition(registry)


def test_boolean_projection_coefficient_is_not_an_integer_definition(registry):
    row = registry.datasets[mapping.DATASET]["discordance_projection"][0]["coefficients"]
    row[row.index(1)] = True
    with pytest.raises(ValueError, match="definition"):
        mapping.definition(registry)


def admitted(registry):
    protocol = mapping._protocol()
    spec = registry.datasets[mapping.DATASET]
    spec["source_manifest_sha256"] = protocol["source_manifest_sha256"]
    spec["source_sha256"] = deepcopy(protocol["source_sha256"])
    spec["implementation_sha256"] = {
        mapping.IMPLEMENTATION: store.digest(Path(mapping.IMPLEMENTATION).read_bytes())
    }
    return protocol


def test_scoped_preservation_allows_unrelated_additions(registry):
    protocol = admitted(registry)
    registry.parameters["synthetic_new_unrelated"] = next(
        iter(registry.parameters.values())
    ).model_copy(deep=True)
    registry.sources["new_unrelated"] = next(iter(registry.sources.values())).model_copy(deep=True)
    registry.datasets["new_unrelated"] = {"status": "synthetic"}
    mapping._registry_contract(registry, protocol)


@pytest.mark.parametrize("group", ["parameters", "sources", "datasets"])
@pytest.mark.parametrize("operation", ["mutation", "deletion"])
def test_preserved_records_refused(registry, group, operation):
    protocol = admitted(registry)
    records = getattr(registry, group)
    key = (
        next(iter(protocol["existing_definition_sha256"]))
        if group == "datasets"
        else protocol[f"preserved_{'parameter' if group == 'parameters' else 'source'}_keys"][0]
    )
    if operation == "deletion":
        del records[key]
    elif group == "datasets":
        records[key]["title"] = "altered"
    elif group == "sources":
        records[key] = records[key].model_copy(update={"citation": "altered"})
    else:
        records[key] = records[key].model_copy(update={"notes": "altered", "title": "altered"})
    with pytest.raises(ValueError):
        mapping._registry_contract(registry, protocol)


@pytest.mark.parametrize("scope", [[], ["missing"], ["bad", "bad"], [False]])
def test_scope_drift_refused(registry, scope):
    protocol = admitted(registry)
    registry.datasets[mapping.DATASET]["preserved_parameter_keys"] = scope
    with pytest.raises(ValueError, match="scope"):
        mapping._registry_contract(registry, protocol)


def test_unadmitted_implementation_refused_before_parser(registry, monkeypatch):
    registry.datasets[mapping.DATASET].pop("implementation_sha256", None)
    monkeypatch.setattr(store, "_frame", lambda *args: pytest.fail("participant parser called"))
    with pytest.raises(ValueError, match="source admission|implementation"):
        mapping.report(registry)


def test_loaded_helper_origin_refused_before_parser(registry, monkeypatch, tmp_path):
    admitted(registry)
    altered = tmp_path / "unadmitted.py"
    altered.write_bytes(b"# Different implementation\n")
    monkeypatch.setattr(mapping, "__file__", str(altered))
    monkeypatch.setattr(store, "_frame", lambda *args: pytest.fail("participant parser called"))
    with pytest.raises(ValueError, match="loaded implementation checksum"):
        mapping.report(registry)


def test_source_manifest_drift_refused_before_parser(registry, monkeypatch, tmp_path):
    admitted(registry)
    (tmp_path / "manifest.json").write_bytes(b"{}")
    monkeypatch.setattr(store, "_frame", lambda *args: pytest.fail("participant parser called"))
    with pytest.raises(ValueError, match="manifest checksum"):
        mapping.report(registry, tmp_path)


@pytest.mark.parametrize("artifact", ["protocol", "raw", "helper", "current_report"])
def test_pinned_artifact_drift_refused_before_parser(registry, monkeypatch, artifact):
    protocol = admitted(registry)
    targets = {
        "protocol": mapping.PROTOCOL_PATH,
        "raw": store.STORE / "GLU_L.xpt",
        "helper": Path("src/demeter/data/survey_joint.py"),
        "current_report": Path("docs/validation/nhanes-2021-2023-glycemic-reconstruction-v1.json"),
    }
    assert (
        artifact == "protocol"
        or targets[artifact].as_posix() in protocol["existing_artifact_sha256"]
    )
    read = store._read

    def changed(path, description):
        return (
            b"changed immutable artifact" if path == targets[artifact] else read(path, description)
        )

    monkeypatch.setattr(store, "_read", changed)
    monkeypatch.setattr(store, "_frame", lambda *args: pytest.fail("participant parser called"))
    with pytest.raises(ValueError, match="checksum"):
        mapping.report(registry)


def test_source_snapshot_and_loaded_identity_for_synthetic_wrapper(registry, monkeypatch):
    protocol = admitted(registry)
    monkeypatch.setattr(store, "_frame", lambda *args: frame())
    report = mapping.report(registry)
    assert report["source_audit_passed"] is True
    assert report["provenance"]["protocol_sha256"] == mapping.PROTOCOL_SHA256
    assert report["provenance"]["source_sha256"] == protocol["source_sha256"]
    loaded = report["provenance"]["loaded_implementation"]
    assert loaded[mapping.IMPLEMENTATION]["loaded_file_verified"] is True
    assert all(not Path(row["admitted_source_path"]).is_absolute() for row in loaded.values())
    assert "__file__" not in nhanes.encoded(report).decode()


def test_physical_old_weight_refused(registry):
    data = frame()
    data["WTSAFPRP"] = data.WTSAF2YR
    with pytest.raises(ValueError, match="only WTSAF2YR"):
        mapping.assess(data, registry)
