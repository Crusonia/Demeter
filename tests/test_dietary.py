import json
import shutil

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from demeter.analysis.experiments import compare, uncertainty
from demeter.cli import app
from demeter.data.dietary import (
    DATASET,
    STORE,
    extract_upf,
    load_dietary,
    rebuild_dietary,
    reference_value,
    survey_mean,
)
from demeter.data.ingest import BUNDLE
from demeter.model import simulate
from demeter.nutrition.exposures import ONTOLOGY, catalog, resolve_diet
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def diet_scenario(key="upf", **changes):
    target = dict(
        target=37.1, unit="percent_energy", reference_period="2021_2023", role="model_effect"
    )
    target.update(changes)
    return Scenario(name="diet", years=3, diet={key: target})


def survey_fixture():
    return pd.DataFrame(
        {
            "weight": [1.0] * 4,
            "SDMVSTRA": [1, 1, 2, 2],
            "SDMVPSU": [1, 2, 1, 2],
            "intake": [0.0, 2.0, 0.0, 2.0],
        }
    )


def test_survey_mean_variance_quantiles_and_weight_scale():
    d = survey_fixture()
    domain = pd.Series([True] * 4)
    result = survey_mean(d, domain, "intake", 0.95, [0.25, 0.5, 0.75])
    assert result["mean"] == 1
    # Each stratum has residuals (-1/4,+1/4); variance = 1/4 + 1/4.
    assert result["standard_error"] ** 2 == pytest.approx(0.5)
    assert result["degrees_of_freedom"] == 2
    assert result["interval"]["low"] == 0
    assert result["interval"]["high"] > 1
    assert result["distribution"]["quantiles"] == {"0.25": 0, "0.5": 0, "0.75": 2}
    d.weight *= 100000
    assert survey_mean(d, domain, "intake", 0.95, [0.25, 0.5, 0.75]) == result


def test_mean_domain_keeps_empty_psus_and_missing_values_outside_domain():
    d = survey_fixture()
    d.intake = [2, np.nan, 0, 0]
    result = survey_mean(d, pd.Series([True, False, True, True]), "intake", 0.95, [0.5])
    assert result["mean"] == pytest.approx(2 / 3)
    assert result["standard_error"] ** 2 == pytest.approx(16 / 81)
    empty = survey_mean(d, pd.Series([False] * 4), "intake", 0.95, [0.5])
    assert empty["mean"] is None and empty["interval"] is None
    with pytest.raises(ValueError, match="Invalid observed"):
        survey_mean(d, pd.Series([True] * 4), "intake", 0.95, [0.5])
    d.loc[1, "SDMVPSU"] = 1
    with pytest.raises(ValueError, match="Singleton"):
        survey_mean(d, pd.Series([True, False, True, True]), "intake", 0.95, [0.5])


def test_offline_rebuild_matches_committed_bytes_and_preserves_references(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Dietary reconstruction attempted a download")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    rebuild_dietary(REGISTRY, destination=tmp_path)
    for name in ("dietary_baselines.json", "dietary_manifest.json"):
        assert (tmp_path / name).read_bytes() == (BUNDLE / name).read_bytes()
    report = load_dietary(REGISTRY, tmp_path)
    assert len(report["rows"]) == 249
    assert len(report["correlations"]) == 4
    assert report["scientific_release_ready"] is False
    for row in report["rows"]:
        assert row["mean"] >= 0 and row["standard_error"] >= 0
        assert row["source"].startswith("https://") and row["population"]
        assert row["comparability_break"] == (row["period"] == "2021_2023")
        if row["exposure"] != "upf":
            assert row["status"] == "estimated"
            assert row["interval"]["low"] <= row["mean"] <= row["interval"]["high"]
            assert 0 <= row["missing_weight_fraction"] <= 1
            quantiles = list(row["distribution"]["quantiles"].values())
            assert quantiles == sorted(quantiles)
    for row in report["correlations"]:
        matrix = np.array(row["matrix"])
        assert np.allclose(matrix, matrix.T)
        assert np.allclose(matrix.diagonal(), 1)
        assert (abs(matrix) <= 1 + 1e-12).all()
        assert "upf" not in row["exposures"]


def test_published_upf_cells_are_extracted_not_reestimated():
    rows = extract_upf(STORE / "db536.htm", REGISTRY.datasets[DATASET]["upf"])
    report = {"rows": rows}
    # Directly published NCHS Data Brief 536 Tables 1, 2, 5.
    latest = reference_value(report, "upf", "2021_2023", "all")
    assert (latest["mean"], latest["standard_error"], latest["n"]) == (53, 0.7, 4881)
    assert latest["age_group"] == "19_plus" and latest["distribution"] is None
    assert reference_value(report, "upf", "2021_2023", "female")["mean"] == 52.7
    assert reference_value(report, "upf", "2013_2014", "all")["mean"] == 55.8
    with pytest.raises(ValueError, match="No unique"):
        reference_value(report, "upf", "2013_2014", "female")


def test_changed_sources_bundles_and_definitions_fail(tmp_path):
    shutil.copyfile(STORE / "manifest.json", tmp_path / "manifest.json")
    receipt = json.loads((tmp_path / "manifest.json").read_bytes())
    first = next(iter(receipt["sources"]))
    (tmp_path / first).write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        rebuild_dietary(REGISTRY, source=tmp_path, destination=tmp_path / "out")
    shutil.copyfile(BUNDLE / "dietary_manifest.json", tmp_path / "dietary_manifest.json")
    (tmp_path / "dietary_baselines.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        load_dietary(REGISTRY, tmp_path)
    changed = REGISTRY.model_copy(deep=True)
    changed.datasets[DATASET]["analysis"]["confidence_level"] = 0.9
    with pytest.raises(ValueError, match="checksum"):
        load_dietary(changed)


@pytest.mark.parametrize("structure", ["legacy", "risk_1", "risk_2"])
def test_absolute_upf_matches_relative_response_and_keeps_observed_provenance(structure):
    scenario = diet_scenario().model_copy(update={"health_structure": structure})
    result = simulate(REGISTRY, scenario)
    relative = simulate(
        REGISTRY,
        Scenario(name="relative", years=3, exposures={"upf": 0.7}, health_structure=structure),
    )
    for a, b in zip(result.annual, relative.annual, strict=True):
        assert a.keys() == b.keys()
        for key in a:
            assert a[key] == pytest.approx(b[key])
    d = result.metadata["dietary_exposures"]
    assert d["upf_multiplier"] == pytest.approx(0.7)
    assert d["changes"]["upf"]["absolute_change"] == pytest.approx(-15.9)
    assert d["changes"]["upf"]["reference"]["status"] == "observed"
    assert len(d["baseline_bundle_sha256"]) == 64
    assert not d["reference_uncertainty_propagated"]
    assert result.validation_only


def test_context_targets_do_not_create_health_effects_or_enter_parameter_sampling():
    scenario = diet_scenario("fiber", target=25, unit="g/day", role="context_only")
    base = Scenario(name="base", years=3)
    result = compare(REGISTRY, base, scenario)
    assert all(v["absolute_delta"] == 0 for v in result["outcomes"].values())
    d = result["intervention_metadata"]["dietary_exposures"]
    assert not d["changes"]["fiber"]["applied_to_health"]
    sampled = uncertainty(REGISTRY, scenario, draws=2, seed=1)
    assert "fiber" not in sampled["sampled_parameters"]
    assert all(v["median"] == 0 for v in sampled["paired_deltas"].values())


def test_absolute_intervention_is_cleared_from_paired_baseline():
    absolute = uncertainty(REGISTRY, diet_scenario(), draws=2, seed=11)
    relative = uncertainty(
        REGISTRY, Scenario(name="relative", years=3, exposures={"upf": 0.7}), draws=2, seed=11
    )
    assert absolute["paired_deltas"]["healthspan"]["median"] > 0
    for key in absolute["paired_deltas"]:
        assert absolute["paired_deltas"][key] == pytest.approx(relative["paired_deltas"][key])


@pytest.mark.parametrize(
    "key,changes,error",
    [
        ("fiber", {"target": 25, "unit": "g/day"}, "independently identified"),
        ("upf", {"unit": "fraction"}, "requires unit"),
        ("upf", {"target": 101}, "physical range"),
        ("upf", {"reference_period": "1900"}, "No unique"),
        ("added_sugar", {"unit": "g/day", "role": "context_only"}, "Unresolved"),
        ("protein_quality", {"unit": "g/day", "role": "context_only"}, "Unresolved"),
    ],
)
def test_no_silent_units_reference_substitution_or_overlapping_activation(key, changes, error):
    with pytest.raises(ValueError, match=error):
        simulate(REGISTRY, diet_scenario(key, **changes))


def test_schema_rejects_duplicates_unknowns_missing_roles_and_nonfinite_targets():
    raw = diet_scenario().model_dump()
    with pytest.raises(ValueError, match="Specify each exposure once"):
        Scenario.model_validate({**raw, "exposures": {"upf": 1}})
    with pytest.raises(ValueError):
        Scenario(name="unknown", diet={"real_food": raw["diet"]["upf"]})
    for changes in (
        {"target": -1},
        {"target": float("nan")},
        {"target": float("inf")},
        {"reference_period": 20212023},
    ):
        with pytest.raises(ValueError):
            diet_scenario(**changes)
    del raw["diet"]["upf"]["role"]
    with pytest.raises(ValueError):
        Scenario.model_validate(raw)
    bypass = diet_scenario().model_copy(update={"exposures": {"upf": 1}})
    with pytest.raises(ValueError, match="Specify each exposure once"):
        simulate(REGISTRY, bypass)


def test_absolute_ranges_sex_references_and_scientific_gate():
    zero = diet_scenario(target=0)
    with pytest.raises(ValueError, match="outside the registered envelope"):
        simulate(REGISTRY, zero)
    assert simulate(REGISTRY, zero.model_copy(update={"allow_extrapolation": True})).metadata[
        "extrapolation"
    ]
    female = diet_scenario(target=52.7).model_copy(update={"sex": "female"})
    assert resolve_diet(REGISTRY, female)["upf_multiplier"] == 1
    with pytest.raises(ValueError, match="Scientific mode blocked"):
        simulate(REGISTRY, female.model_copy(update={"mode": "scientific"}))


def test_catalog_cannot_activate_overlapping_pathways_by_registry_edit():
    report = catalog(REGISTRY)
    assert len(report["definitions"]) == 13
    assert report["definitions"]["upf"]["kind"] == "food_category"
    assert report["definitions"]["fiber"]["kind"] == "nutrient"
    assert report["definitions"]["added_sugar"]["availability"] == "unresolved"
    changed = REGISTRY.model_copy(deep=True)
    changed.datasets[ONTOLOGY]["definitions"]["fiber"].update(
        availability="active_validation", effect_parameters=["beta_upf_progression"]
    )
    with pytest.raises(ValueError, match="overlapping"):
        resolve_diet(changed, diet_scenario())
    changed = REGISTRY.model_copy(deep=True)
    changed.datasets[ONTOLOGY]["definitions"]["fiber"]["unit"] = "mg/day"
    with pytest.raises(ValueError, match="does not match its observed reference"):
        resolve_diet(changed, diet_scenario("fiber", unit="mg/day", role="context_only"))


def test_cli_catalog_and_yaml_scenarios(tmp_path):
    output = tmp_path / "exposures.json"
    run = CliRunner().invoke(app, ["food-exposures", "--output", str(output)])
    assert run.exit_code == 0, run.output
    assert not json.loads(output.read_text())["scientific_release_ready"]
    run = CliRunner().invoke(
        app, ["evidence", "dietary", "--output", str(tmp_path / "dietary.json")]
    )
    assert run.exit_code == 0, run.output
    for name in ("dietary_upf_30", "dietary_context"):
        scenario = Scenario.from_yaml(f"scenarios/{name}.yaml")
        assert simulate(REGISTRY, scenario).validation_only
