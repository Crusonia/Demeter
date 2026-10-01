"""Publication reproduction and independent synthetic categorical-model checks."""

from __future__ import annotations

import copy
import json
import math
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pytest
from scipy.stats import binom

import demeter.analysis.geelong_labels as module
from demeter.data.ingest import digest
from demeter.schema import EvidenceRegistry

PROTOCOL = Path("docs/validation/geelong-label-protocol-v1.json")
PRIVATE = "UNTRUSTED_SOURCE_OR_EXCEPTION_MARKER"


@pytest.fixture(scope="session")
def protocol():
    return json.loads(PROTOCOL.read_bytes())


@pytest.fixture(scope="session")
def source_bytes(protocol):
    return Path(protocol["source"]["intended_archive_path"]).read_bytes()


@pytest.fixture(scope="session")
def registered():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


@pytest.fixture
def synthetic_reported():
    """Arbitrary software observations, not another empirical evidence source."""
    return {
        "counts": {
            "normal_start": {"normoglycaemia": 2, "ifg_ada": 1, "source_diabetes": 1},
            "ifg_ada_start": {"normoglycaemia": 0, "ifg_ada": 3, "source_diabetes": 1},
        },
        "row_totals": {"normal_start": 4, "ifg_ada_start": 4},
        "cohort_crosscheck": {
            "paired_assessed_n": 9,
            "baseline_diabetes_n": 1,
            "progression_analysis_n": 8,
        },
        "locators": {"purpose": "explicit synthetic mathematical fixture"},
    }


def _repinned_parser_fixture(content: bytes, protocol: dict) -> dict:
    """Exercise semantic checks even after an outer checksum is updated."""
    selected = copy.deepcopy(protocol)
    selected["source"]["sha256"] = digest(content)
    selected["source"]["size_bytes"] = len(content)
    return selected


def _mutated_xml(source: bytes, operation) -> bytes:
    root = ET.fromstring(source)
    operation(root)
    return ET.tostring(root, encoding="utf-8")


def _selected_paragraph(root: ET.Element) -> ET.Element:
    section = root.find(".//sec[@id='sec3.4']")
    assert section is not None
    return next(
        p for p in section.findall("p") if "Most men with normoglycaemia" in "".join(p.itertext())
    )


def _replace_text(element: ET.Element, old: str, new: str) -> None:
    for node in element.iter():
        for field in ("text", "tail"):
            value = getattr(node, field)
            if value is not None and old in value:
                setattr(node, field, value.replace(old, new, 1))
                return
    raise AssertionError("Synthetic mutation did not bind to its intended source token")


def _failed(report: dict) -> None:
    assert report["source_audit_passed"] is False
    assert report["working_fit_performed"] is False
    for key in (
        "clinical_transition_fit_performed",
        "engine_activation_allowed",
        "independent_validation",
        "scientific_release_ready",
    ):
        assert report[key] is False
    for key in ("observed_labels", "working_fit", "joint_covariance", "intervals"):
        assert report[key] is None
    assert PRIVATE not in json.dumps(report, allow_nan=False)


def test_real_publication_reproduces_only_frozen_labels(source_bytes, protocol):
    reported = module.extract_reported(source_bytes, protocol)
    assert reported["counts"] == {
        "normal_start": {"normoglycaemia": 281, "ifg_ada": 32, "source_diabetes": 11},
        "ifg_ada_start": {"normoglycaemia": 44, "ifg_ada": 27, "source_diabetes": 21},
    }
    assert reported["row_totals"] == {"normal_start": 324, "ifg_ada_start": 92}
    assert reported["cohort_crosscheck"] == {
        "paired_assessed_n": 446,
        "baseline_diabetes_n": 30,
        "progression_analysis_n": 416,
    }
    assert "IFG-WHO" in reported["locators"]["counts"]
    assert not any(key in reported for key in ("who_counts", "person_years", "death_counts"))


@pytest.mark.parametrize("probabilities", [(1.0, 0.0, 0.0), (0.0, 0.3, 0.7), (0.2, 0.3, 0.5)])
def test_multinomial_mass_matches_factorial_oracle_and_normalizes(probabilities):
    n = 4  # Small exhaustive software experiment.
    total = 0.0
    for a in range(n + 1):
        for b in range(n - a + 1):
            counts = (a, b, n - a - b)
            coefficient = math.factorial(n) // math.prod(math.factorial(c) for c in counts)
            expected = coefficient * math.prod(
                p**c for p, c in zip(probabilities, counts, strict=True)
            )
            actual = math.exp(module.multinomial_log_likelihood(counts, probabilities))
            assert actual == pytest.approx(expected, abs=1e-15)
            total += actual
    assert total == pytest.approx(1.0, abs=1e-14)


def test_impossible_boundary_is_minus_infinity_not_nan():
    assert module.multinomial_log_likelihood((4, 0, 0), (1.0, 0.0, 0.0)) == 0
    assert module.multinomial_log_likelihood((3, 1, 0), (1.0, 0.0, 0.0)) == -math.inf


def test_log_likelihood_concavity_and_relative_mle_have_independent_oracles():
    counts = (2, 1, 1)
    left, right = (0.1, 0.2, 0.7), (0.7, 0.2, 0.1)
    midpoint = tuple((a + b) / 2 for a, b in zip(left, right, strict=True))
    assert (
        module.multinomial_log_likelihood(counts, midpoint)
        >= (
            module.multinomial_log_likelihood(counts, left)
            + module.multinomial_log_likelihood(counts, right)
        )
        / 2
    )
    mle, alternative = (0.5, 0.25, 0.25), (0.4, 0.4, 0.2)
    relative = module.multinomial_log_likelihood(
        counts, alternative
    ) - module.multinomial_log_likelihood(counts, mle)
    oracle = sum(c * math.log(p / q) for c, p, q in zip(counts, alternative, mle, strict=True))
    assert relative == pytest.approx(oracle, abs=1e-14)
    assert relative < 0


@pytest.mark.parametrize(
    "counts,probabilities",
    [
        ((True, 1, 1), (0.2, 0.4, 0.4)),
        ((1.0, 1, 1), (0.2, 0.4, 0.4)),
        ((-1, 1, 1), (0.2, 0.4, 0.4)),
        ((1, 1, 1), (True, 0.0, 0.0)),
        ((1, 1, 1), ("0.2", 0.4, 0.4)),
        ((1, 1, 1), (-0.1, 0.5, 0.6)),
        ((1, 1, 1), (0.2, 0.2, 0.2)),
        ((1, 1, 1), (math.inf, 0.0, 0.0)),
        ((1, 1, 1), (math.nan, 0.0, 0.0)),
        ((1, 1, 1), (0.5, 0.5)),
        ((1, 1, 1), (10**1000, 0.0, 0.0)),
        ((10**1000, 1, 1), (0.2, 0.4, 0.4)),
        ((1, 1, 1), np.ma.array([0.2, 0.4, 0.4], mask=[False, True, False])),
        (np.ma.array([1, 1, 1], mask=[False, True, False]), (0.2, 0.4, 0.4)),
        ((1, 1, 1), [[0.2, 0.4, 0.4]]),
    ],
)
def test_invalid_count_and_probability_domains_are_not_coerced(counts, probabilities):
    with pytest.raises(ValueError):
        module.multinomial_log_likelihood(counts, probabilities)


def test_numpy_integer_counts_and_real_probabilities_work():
    result = module.multinomial_log_likelihood(np.array([2, 1, 1]), np.array([0.5, 0.25, 0.25]))
    assert math.exp(result) == pytest.approx(3 / 16)


def test_empty_generic_experiment_has_unit_mass_but_source_rows_must_be_nonempty(
    synthetic_reported, protocol
):
    assert module.multinomial_log_likelihood((0, 0, 0), (0.2, 0.4, 0.4)) == 0
    synthetic_reported["counts"]["normal_start"] = dict.fromkeys(module.DESTINATIONS, 0)
    synthetic_reported["row_totals"]["normal_start"] = 0
    with pytest.raises(ValueError):
        module.analyze_labels(synthetic_reported, protocol)


def test_synthetic_joint_covariance_matches_categorical_sampling_oracle(
    synthetic_reported, protocol
):
    result = module.analyze_labels(synthetic_reported, protocol)
    joint = result["joint_covariance"]
    coordinates = [
        {"row": row, "destination": label} for row in module.ROWS for label in module.DESTINATIONS
    ]
    assert joint["coordinates"] == coordinates
    actual = np.asarray(joint["covariance"])
    oracle = np.zeros((6, 6))
    for block, row in enumerate(module.ROWS):
        total = synthetic_reported["row_totals"][row]
        p = [Fraction(synthetic_reported["counts"][row][k], total) for k in module.DESTINATIONS]
        # Enumerate the possible one-person categorical observations, then use
        # independent-average variance scaling. No matrix repair or fitted rate.
        for j in range(3):
            for k in range(3):
                expectation = sum(
                    p[outcome] * (Fraction(outcome == j) - p[j]) * (Fraction(outcome == k) - p[k])
                    for outcome in range(3)
                )
                oracle[3 * block + j, 3 * block + k] = float(expectation / total)
    np.testing.assert_array_equal(actual, oracle)
    np.testing.assert_array_equal(actual, actual.T)
    np.testing.assert_array_equal(actual[:3, 3:], np.zeros((3, 3)))
    np.testing.assert_allclose(actual.sum(axis=1), 0, atol=1e-16)
    assert np.linalg.eigvalsh(actual).min() >= -1e-16
    assert np.linalg.matrix_rank(actual[:3, :3], tol=1e-14) == 2
    assert np.linalg.matrix_rank(actual[3:, 3:], tol=1e-14) == 1
    assert np.linalg.matrix_rank(actual, tol=1e-14) == 3
    assert joint["cross_row_independence_assumed"] is True
    assert joint["singularity_preserved"] is True
    assert joint["matrix_repair_performed"] is False
    assert joint["selection_measurement_transport_uncertainty_included"] is False
    json.dumps(result, allow_nan=False)


def test_two_interior_rows_preserve_four_dimensional_singular_joint_uncertainty(
    synthetic_reported, protocol
):
    synthetic_reported["counts"]["ifg_ada_start"] = {
        "normoglycaemia": 1,
        "ifg_ada": 2,
        "source_diabetes": 1,
    }
    covariance = np.asarray(
        module.analyze_labels(synthetic_reported, protocol)["joint_covariance"]["covariance"]
    )
    assert np.linalg.matrix_rank(covariance, tol=1e-14) == 4
    for row_sum in ([1, 1, 1, 0, 0, 0], [0, 0, 0, 1, 1, 1]):
        np.testing.assert_allclose(covariance @ row_sum, 0, atol=1e-16)


def test_bonferroni_intervals_invert_binomial_tails_for_all_six_cells(synthetic_reported, protocol):
    result = module.analyze_labels(synthetic_reported, protocol)
    intervals = result["intervals"]
    family_alpha = 1 - protocol["working_likelihood"]["confidence_level"]
    cell_alpha = family_alpha / 6
    assert intervals["multiplicity"] == 6
    assert intervals["effective_cell_confidence_level"] == pytest.approx(1 - cell_alpha)
    assert intervals["simultaneous_confidence_level"] == 0.95
    for coordinate, (low, high) in zip(intervals["coordinates"], intervals["bounds"], strict=True):
        row, category = coordinate["row"], coordinate["destination"]
        count, total = (
            synthetic_reported["counts"][row][category],
            synthetic_reported["row_totals"][row],
        )
        assert 0 <= low <= count / total <= high <= 1
        if count == 0:
            assert low == 0
        else:
            assert binom.sf(count - 1, total, low) == pytest.approx(cell_alpha / 2, abs=1e-14)
        if count == total:
            assert high == 1
        else:
            assert binom.cdf(count, total, high) == pytest.approx(cell_alpha / 2, abs=1e-14)
    assert intervals["selection_measurement_transport_uncertainty_included"] is False
    assert "working model only" in intervals["coverage_scope"]


def test_all_success_interval_boundary_and_normalized_joint_mass(synthetic_reported, protocol):
    synthetic_reported["counts"]["normal_start"] = {
        "normoglycaemia": 4,
        "ifg_ada": 0,
        "source_diabetes": 0,
    }
    result = module.analyze_labels(synthetic_reported, protocol)
    assert result["intervals"]["bounds"][0][1] == 1
    row_log = result["working_fit"]["row_log_likelihood_at_mle"]
    assert row_log["normal_start"] == {"value": 0.0, "status": "finite"}
    # The other row has probability 4*(3/4)^3*(1/4) for counts (0,3,1).
    assert math.exp(result["working_fit"]["joint_log_likelihood_at_mle"]["value"]) == pytest.approx(
        Fraction(27, 64)
    )


@pytest.mark.parametrize(
    "change", ["missing_category", "bool_bucket", "row_total", "cohort", "mode"]
)
def test_incomplete_synthetic_tables_and_nonboolean_mode_reject(
    synthetic_reported, protocol, change
):
    options = {}
    if change == "missing_category":
        del synthetic_reported["counts"]["normal_start"]["ifg_ada"]
    elif change == "bool_bucket":
        synthetic_reported["counts"]["normal_start"]["ifg_ada"] = True
    elif change == "row_total":
        synthetic_reported["row_totals"]["normal_start"] = 5
    elif change == "cohort":
        synthetic_reported["cohort_crosscheck"]["paired_assessed_n"] = 10
    else:
        options["working_likelihood"] = 1
    with pytest.raises(ValueError):
        module.analyze_labels(synthetic_reported, protocol, **options)


@pytest.mark.parametrize("kind", ["doi", "pmcid", "title", "license", "copyright"])
def test_source_identity_and_rights_fail_even_with_updated_checksum(source_bytes, protocol, kind):
    paths = {
        "doi": ".//article-id[@pub-id-type='doi']",
        "pmcid": ".//article-id[@pub-id-type='pmcid']",
        "title": ".//article-title",
        "license": ".//license",
        "copyright": ".//copyright-statement",
    }

    def mutate(root):
        selected = root.find(paths[kind])
        assert selected is not None
        selected.clear()
        selected.text = PRIVATE

    content = _mutated_xml(source_bytes, mutate)
    with pytest.raises(ValueError):
        module.extract_reported(content, _repinned_parser_fixture(content, protocol))


@pytest.mark.parametrize("section_id", ["sec2.2", "sec3.4"])
@pytest.mark.parametrize("change", ["missing", "duplicate", "heading"])
def test_selected_section_is_unique_and_exact(source_bytes, protocol, section_id, change):
    def mutate(root):
        selected = root.find(f".//sec[@id='{section_id}']")
        assert selected is not None
        parent = next(node for node in root.iter() if selected in list(node))
        if change == "missing":
            parent.remove(selected)
        elif change == "duplicate":
            parent.append(copy.deepcopy(selected))
        else:
            selected.find("title").text = PRIVATE

    content = _mutated_xml(source_bytes, mutate)
    with pytest.raises(ValueError):
        module.extract_reported(content, _repinned_parser_fixture(content, protocol))


@pytest.mark.parametrize("replacement", ["-1", "281.0", "２８１", "282"])
def test_invalid_or_inconsistent_selected_bucket_is_not_repaired(
    source_bytes, protocol, replacement
):
    content = _mutated_xml(
        source_bytes, lambda root: _replace_text(_selected_paragraph(root), "281", replacement)
    )
    with pytest.raises(ValueError):
        module.extract_reported(content, _repinned_parser_fixture(content, protocol))


@pytest.mark.parametrize("old,new", [("IFG-ADA", "IFG-WHO"), ("progressed to IFG-ADA", PRIVATE)])
def test_missing_or_wrong_category_binding_is_not_zero_completed(source_bytes, protocol, old, new):
    content = _mutated_xml(
        source_bytes, lambda root: _replace_text(_selected_paragraph(root), old, new)
    )
    with pytest.raises(ValueError):
        module.extract_reported(content, _repinned_parser_fixture(content, protocol))


def test_duplicate_selected_paragraph_is_rejected(source_bytes, protocol):
    def mutate(root):
        root.find(".//sec[@id='sec3.4']").append(copy.deepcopy(_selected_paragraph(root)))

    content = _mutated_xml(source_bytes, mutate)
    with pytest.raises(ValueError):
        module.extract_reported(content, _repinned_parser_fixture(content, protocol))


def test_independent_methods_denominator_conflict_is_rejected(source_bytes, protocol):
    def mutate(root):
        selected = root.find(".//sec[@id='sec2.2']")
        assert selected is not None
        _replace_text(selected, "446", "447")

    content = _mutated_xml(source_bytes, mutate)
    with pytest.raises(ValueError):
        module.extract_reported(content, _repinned_parser_fixture(content, protocol))


def test_real_audit_is_offline_immutable_and_not_clinical(registered):
    before = registered.model_dump(mode="json")
    report = module.audit_geelong_labels(registered)
    assert report["source_audit_passed"] is True
    assert report["working_fit_performed"] is True
    assert registered.model_dump(mode="json") == before
    for key in (
        "clinical_transition_fit_performed",
        "engine_activation_allowed",
        "independent_validation",
        "scientific_release_ready",
    ):
        assert report[key] is False
    json.dumps(report, allow_nan=False)


def test_descriptive_audit_never_calls_likelihood(registered, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Descriptive reproduction must not call working likelihood")

    monkeypatch.setattr(module, "multinomial_log_likelihood", forbidden)
    report = module.audit_geelong_labels(registered, working_likelihood=False)
    assert report["source_audit_passed"] is True
    assert report["working_fit_performed"] is False
    assert report["observed_labels"] is not None
    for key in ("working_fit", "joint_covariance", "intervals"):
        assert report[key] is None


@pytest.mark.parametrize("change", ["missing", "changed"])
def test_absent_or_changed_bytes_return_sanitized_failure(
    registered, source_bytes, tmp_path, change
):
    source = tmp_path / f"{PRIVATE}.xml"
    if change == "changed":
        source.write_bytes(source_bytes + PRIVATE.encode())
    _failed(module.audit_geelong_labels(registered, source_path=source))


def test_unreadable_source_returns_sanitized_failure(registered, tmp_path, monkeypatch):
    source = tmp_path / "synthetic.xml"
    source.write_bytes(b"Synthetic unreadable document")
    original = Path.read_bytes

    def read(path):
        if path == source:
            raise PermissionError(PRIVATE)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    _failed(module.audit_geelong_labels(registered, source_path=source))


def test_registry_count_drift_fails_without_mutating_inputs(registered):
    selected = registered.model_copy(deep=True)
    key = "geelong_normal_start_normoglycaemia_n"
    selected.parameters[key] = selected.parameters[key].model_copy(update={"value": 282})
    before = selected.model_dump(mode="json")
    _failed(module.audit_geelong_labels(selected))
    assert selected.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "change",
    [
        "active_role",
        "clinical_allowed",
        "source_hash",
        "duplicate_parameters",
        "working_assumptions",
    ],
)
def test_dataset_cannot_promote_or_redefine_the_frozen_source(registered, change):
    selected = registered.model_copy(deep=True)
    spec = selected.datasets[module.DATASET]
    if change == "active_role":
        spec["model_role"] = "active"
    elif change == "clinical_allowed":
        spec["clinical_fit_allowed"] = True
    elif change == "source_hash":
        spec["source_sha256"] = "0" * 64
    elif change == "duplicate_parameters":
        spec["parameter_keys"][-1] = spec["parameter_keys"][0]
    else:
        spec["working_likelihood"]["assumptions_empirically_established"] = True
    _failed(module.audit_geelong_labels(selected))


@pytest.mark.parametrize(
    "field,value",
    [("model_role", "active"), ("source_id", "another_source"), ("population", PRIVATE)],
)
def test_parameter_context_and_role_drift_fail_closed(registered, field, value):
    selected = registered.model_copy(deep=True)
    key = "geelong_normal_start_normoglycaemia_n"
    selected.parameters[key] = selected.parameters[key].model_copy(update={field: value})
    _failed(module.audit_geelong_labels(selected))


def test_registered_interval_drift_is_not_repaired_or_promoted(registered):
    selected = registered.model_copy(deep=True)
    key = "geelong_normal_start_normoglycaemia_probability"
    parameter = selected.parameters[key]
    changed = parameter.uncertainty.model_copy(update={"low": parameter.uncertainty.low + 0.01})
    selected.parameters[key] = parameter.model_copy(update={"uncertainty": changed})
    _failed(module.audit_geelong_labels(selected))


def test_protocol_cannot_be_coordinately_repinned_in_registry(registered, tmp_path):
    selected = registered.model_copy(deep=True)
    spec = selected.datasets[module.DATASET]
    protocol = json.loads(Path(spec["protocol_path"]).read_bytes())
    protocol["working_likelihood"]["confidence_level"] = 0.9
    path = tmp_path / "repinned-protocol.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    spec.update(protocol_path=str(path), protocol_sha256=digest(path.read_bytes()))
    _failed(module.audit_geelong_labels(selected))


def test_aggregate_bundle_semantics_fail_even_with_updated_outer_checksum(registered, tmp_path):
    selected = registered.model_copy(deep=True)
    spec = selected.datasets[module.DATASET]
    bundle = json.loads(Path(spec["bundle_path"]).read_bytes())
    bundle["counts"]["normal_start"]["normoglycaemia"] = 282
    path = tmp_path / "repinned-bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    spec.update(bundle_path=str(path), bundle_sha256=digest(path.read_bytes()))
    _failed(module.audit_geelong_labels(selected))


@pytest.mark.parametrize(
    "content", [b"<not-an-article />", b"<!DOCTYPE article><article />", b"<article>"]
)
def test_malformed_or_entity_bearing_xml_is_not_accepted(protocol, content):
    with pytest.raises(ValueError):
        module.extract_reported(content, _repinned_parser_fixture(content, protocol))
