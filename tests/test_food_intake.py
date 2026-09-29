from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from demeter.analysis.food_intake import DATASET, analyze_daily, reproduce_intake
from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded, storage_numbers
from demeter.schema import EvidenceRegistry


@pytest.fixture
def example():
    """Labeled synthetic pairs; no participant data copied into test fixtures."""
    spec = deepcopy(
        EvidenceRegistry.from_yaml("evidence/parameters.yaml").datasets[DATASET]["analysis"]
    )
    spec.update(
        participants=4,
        days_per_diet=2,
        published_difference_kcal_per_day=250,
        published_standard_error_kcal_per_day=65,
    )
    rows = []
    for person, delta in enumerate((100, 200, 300, 400)):
        order = "PU" if person < 2 else "UP"
        for period, diet in enumerate(spec["sequences"][order]):
            for day, fluctuation in enumerate((-5, 5), 1):
                rows.append(
                    dict(
                        StudyID=f"synthetic-{person}",
                        Period=diet,
                        DietOrder=order,
                        Day=period * 2 + day,
                        DaysOnDiet=day,
                        EI=1000 + person * 100 + fluctuation + (delta if diet == "PROC" else 0),
                    )
                )
    return pd.DataFrame(rows), spec


def test_paired_arithmetic_and_period_sensitivity_are_participant_level(example):
    frame, spec = example
    result = analyze_daily(frame, spec)
    primary = result["paired_difference"]
    assert primary["participants"] == 4 and primary["degrees_of_freedom"] == 3
    assert primary["mean"] == 250
    assert primary["standard_error"] == pytest.approx(np.sqrt(50000 / 3) / 2)
    assert primary["sufficient_statistics"] == {"sum": 1000, "sum_squares": 300000}
    # Independent t-table value for df=3, two-sided 95%.
    half_width = 3.182446305 * np.sqrt(50000 / 3) / 2
    assert primary["interval"] == pytest.approx([250 - half_width, 250 + half_width])
    sensitivity = result["period_sensitivity"]
    assert sensitivity["parameter_order"] == ["diet_contrast", "common_period_effect"]
    assert sensitivity["degrees_of_freedom"] == 2
    assert sensitivity["terms"]["diet_contrast"]["value"] == pytest.approx(250)
    assert sensitivity["terms"]["common_period_effect"]["value"] == pytest.approx(100)
    assert np.asarray(sensitivity["covariance"]) == pytest.approx(np.diag([1250, 1250]))
    assert result["by_randomized_sequence"]["PU"]["mean"] == 150
    assert result["by_randomized_sequence"]["UP"]["mean"] == 350
    assert result["published_reproduction_passed"]
    assert analyze_daily(frame.sample(frac=1, random_state=42), spec) == result
    assert "synthetic-0" not in json.dumps(result)


@pytest.mark.parametrize(
    "problem", ["missing", "duplicate", "order", "diet", "day", "inf", "negative", "id"]
)
def test_incomplete_or_inconsistent_records_are_rejected(example, problem):
    frame, spec = example
    if problem == "missing":
        frame = frame.iloc[:-1]
    elif problem == "duplicate":
        frame = pd.concat([frame, frame.iloc[:1]])
    else:
        column, value = {
            "order": ("DietOrder", "UP"),
            "diet": ("Period", "unknown"),
            "day": ("Day", 1.5),
            "inf": ("EI", np.inf),
            "negative": ("EI", -1),
            "id": ("StudyID", ""),
        }[problem]
        frame[column] = frame[column].astype(object)
        frame.loc[0, column] = value
    with pytest.raises(ValueError):
        analyze_daily(frame, spec)


def test_null_is_retained_and_days_do_not_supply_extra_degrees_of_freedom(example):
    frame, spec = example
    frame["EI"] = 1000
    result = analyze_daily(frame, spec)
    assert result["paired_difference"]["mean"] == 0
    assert result["paired_difference"]["interval"] is None
    assert result["paired_difference"]["two_sided_p_value"] is None
    assert not result["published_reproduction_passed"]
    assert result["paired_difference"]["degrees_of_freedom"] == 3


def test_protocol_and_archive_are_verified_before_decoding(tmp_path, monkeypatch):
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")

    def forbidden(*args, **kwargs):
        pytest.fail("A mismatched archive/protocol must not be decoded or downloaded")

    monkeypatch.setattr(pd, "read_sas", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    archive = tmp_path / "wrong.zip"
    archive.write_bytes(b"not the pinned author source")
    with pytest.raises(ValueError, match="archive checksum"):
        reproduce_intake(registry, archive)
    registry.datasets[DATASET]["protocol_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="protocol checksum"):
        reproduce_intake(registry, tmp_path / "absent.zip")


def test_cli_outputs_only_canonical_aggregate_results_and_rejects_estimate_drift(
    example, tmp_path, monkeypatch
):
    import yaml

    frame, analysis = example
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = registry.datasets[DATASET]
    protocol = json.loads(Path(spec["protocol_path"]).read_bytes())
    raw, code = b"synthetic SAS-reader fixture", b"synthetic author-code fixture; not executed"
    stream = BytesIO()
    with ZipFile(stream, "w") as bundle:
        bundle.writestr(protocol["member"], raw)
        bundle.writestr("ADLDocumentation1.sas", code)
    content = stream.getvalue()
    archive = tmp_path / "synthetic.zip"
    archive.write_bytes(content)
    protocol.update(
        analysis=analysis,
        archive_sha256=digest(content),
        member_sha256=digest(raw),
        author_code_sha256=digest(code),
    )
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_bytes(encoded(protocol))
    spec.update(
        analysis=analysis,
        protocol_path=str(protocol_path),
        protocol_sha256=digest(protocol_path.read_bytes()),
    )
    registry.sources[spec["source_id"]].sha256 = digest(content)
    parameter = registry.parameters[spec["estimate_parameter"]]
    primary = storage_numbers(analyze_daily(frame, analysis)["paired_difference"])
    parameter.value = primary["mean"]
    parameter.uncertainty.low, parameter.uncertainty.high = primary["interval"]
    monkeypatch.setattr(pd, "read_sas", lambda *a, **k: frame)

    def no_network(*args, **kwargs):
        pytest.fail("Food-intake reproduction must stay offline")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    expected = reproduce_intake(registry, archive)
    assert expected["model_role"] == "benchmark_only"
    assert not expected["scientific_release_ready"]
    assert not expected["provenance"]["individual_results_exported"]
    registry_path = tmp_path / "evidence.yaml"
    registry_path.write_text(yaml.safe_dump(registry.model_dump(mode="json")), encoding="utf8")
    output = tmp_path / "result.json"
    run = CliRunner().invoke(
        app,
        [
            "evidence",
            "food-intake",
            "--archive",
            str(archive),
            "--evidence",
            str(registry_path),
            "--output",
            str(output),
        ],
    )
    assert run.exit_code == 0, run.output
    assert output.read_bytes() == encoded(expected)
    parameter.value += 1
    with pytest.raises(ValueError, match="Registered benchmark estimate"):
        reproduce_intake(registry, archive)


def test_committed_aggregate_receipt_reconciles_independently():
    report = json.loads(Path("docs/validation/issue-58-food-intake.json").read_bytes())
    result = report["results"]
    primary = result["paired_difference"]
    n = primary["participants"]
    sums = primary["sufficient_statistics"]
    mean = sums["sum"] / n
    se = np.sqrt((sums["sum_squares"] - sums["sum"] ** 2 / n) / (n - 1) / n)
    assert mean == pytest.approx(primary["mean"])
    assert se == pytest.approx(primary["standard_error"])
    assert sum(r["participants"] for r in result["by_randomized_sequence"].values()) == n
    assert sum(
        r["sufficient_statistics"]["sum"] for r in result["by_randomized_sequence"].values()
    ) == pytest.approx(sums["sum"])
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = registry.datasets[DATASET]
    assert report["provenance"]["definition_sha256"] == digest(encoded(spec))
    assert report["provenance"]["transform_sha256"] == digest(
        Path("src/demeter/analysis/food_intake.py").read_bytes()
    )
    assert registry.parameters[spec["estimate_parameter"]].model_role == "benchmark_only"
