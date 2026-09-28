import json
import shutil

import numpy as np
import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.ingest import BUNDLE
from demeter.data.linked_mortality import (
    LAYOUT,
    MORTALITY_FILE,
    STORE,
    audit,
    definition,
    load_linked_mortality,
    read_mortality,
    read_store,
    rebuild_linked_mortality,
)
from demeter.schema import EvidenceRegistry

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def record(seqn, eligibility, status=".", interview=".", examination="."):
    row = [" "] * 48
    for key, value in zip(LAYOUT, (seqn, eligibility, status, interview, examination), strict=True):
        start, end = LAYOUT[key]
        row[start:end] = str(value).ljust(end - start)
    return "".join(row).rstrip() + "\n"


def test_official_fixed_width_layout_preserves_missingness_and_short_final_field(tmp_path):
    path = tmp_path / "fixture.dat"
    path.write_text(record(101, 1, 1, 11, 9) + record(102, 2) + record(103, 3))
    frame = read_mortality(path)
    assert frame.loc[0, "PERMTH_EXM"] == 9
    assert frame.loc[0, "MORTSTAT"] == 1
    assert frame.loc[1:, "MORTSTAT"].isna().all()


@pytest.mark.parametrize(
    "content, message",
    [
        (record(1, 1, 0, 12, 11) * 2, "duplicate"),
        (record(1, 3, 0), "Ineligible"),
        (record(1, 1), "vital status"),
        (record(1, 1, 7, 12, 11), "vital status"),
        (record(1, 4), "eligibility"),
        (record(1, 1, 1, 10, 11), "follow-up"),
        (record(1, 1, 1, 10, -1), "follow-up"),
        ("short\n", "record length"),
    ],
)
def test_corrupt_linkage_records_fail(tmp_path, content, message):
    path = tmp_path / "invalid.dat"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        read_mortality(path)


@pytest.fixture(scope="module")
def linked_frame():
    return read_store()[0]


def test_official_records_join_and_missing_outcomes_never_become_survival(linked_frame):
    report = audit(linked_frame, definition(REGISTRY))
    c = report["counts"]
    # DEMO_G official codebook total; joins may not duplicate or drop respondents.
    assert c["source_n"] == 9756
    assert c["complete_baseline_n"] == c["linked_complete_n"] + c["ineligible_complete_n"]
    assert c["adult_nonpregnant_n"] == c["complete_baseline_n"] + c["missing_glycemic_n"]
    total = [d for d in report["domains"] if d["age_group"] == "20_plus" and d["sex"] == "all"]
    assert sum(d["linked_n"] for d in total) == c["linked_complete_n"]
    for d in report["domains"]:
        assert d["complete_baseline_n"] == d["linked_n"] + d["ineligible_n"]
        assert 0 <= d["deaths_n"] <= d["linked_n"]
    assert not report["scientific_release_ready"]
    assert not report["independent_holdout"]
    assert report["design"]["weight"] == "WTSAF2YR"


def test_unlinked_and_missing_glycemic_rows_remain_in_attrition_audit(linked_frame):
    frame = linked_frame.copy()
    row = frame.index[
        (frame.WTSAF2YR > 0)
        & (frame.RIDAGEYR > 44)
        & frame.LBXGH.notna()
        & frame.LBXGLU.notna()
        & frame.DIQ010.isin([1, 2, 3])
        & (frame.ELIGSTAT == 1)
    ][0]
    before = audit(frame, definition(REGISTRY))["counts"]
    frame.loc[row, "ELIGSTAT"] = 3
    frame.loc[row, ["MORTSTAT", "PERMTH_INT", "PERMTH_EXM"]] = np.nan
    after = audit(frame, definition(REGISTRY))["counts"]
    assert after["complete_baseline_n"] == before["complete_baseline_n"]
    assert after["ineligible_complete_n"] == before["ineligible_complete_n"] + 1
    frame.loc[row, "LBXGLU"] = np.nan
    missing = audit(frame, definition(REGISTRY))["counts"]
    assert missing["missing_glycemic_n"] == before["missing_glycemic_n"] + 1


def test_offline_rebuild_is_byte_identical(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Offline reconstruction used network")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    rebuild_linked_mortality(REGISTRY, destination=tmp_path)
    assert load_linked_mortality(REGISTRY, tmp_path) == load_linked_mortality(REGISTRY)
    for name in ("linked_mortality_audit.json", "linked_mortality_manifest.json"):
        assert (tmp_path / name).read_bytes() == (BUNDLE / name).read_bytes()


def test_corrupt_source_and_definition_drift_rejected(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    shutil.copyfile(STORE / "manifest.json", source / "manifest.json")
    (source / "DEMO_G.xpt").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="source checksum"):
        read_store(source)
    changed = REGISTRY.model_copy(deep=True)
    changed.datasets["nhanes_glycemic_prevalence"]["analysis"]["glucose_prediabetes_min"] = 101
    with pytest.raises(ValueError, match="definition changed"):
        load_linked_mortality(changed)


def test_cli_reports_feasibility_not_fitted_parameters():
    response = CliRunner().invoke(app, ["evidence", "linked-mortality"])
    assert response.exit_code == 0, response.output
    report = json.loads(response.output)
    assert report["model_role"] == "feasibility_only"
    assert "hazard_ratio" not in report
    assert MORTALITY_FILE in report["provenance"]["source_sha256"]
