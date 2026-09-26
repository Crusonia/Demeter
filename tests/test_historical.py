import copy
import json

import numpy as np
import pytest
from typer.testing import CliRunner

from demeter.analysis.historical import backtest_series, forecast, historical_backtest, metrics
from demeter.cli import app
from demeter.data.historical import load_history, rebuild_history, validate_series
from demeter.schema import EvidenceRegistry


def fixture_series():
    return {
        "id": "fixture",
        "domain": "mortality",
        "unit": "years",
        "observations": [
            {"year": y, "value": 10 + (y - 1970) * 0.2, "segment": "same"}
            for y in range(1970, 2025)
        ],
    }


def test_linear_trajectory_has_exact_forecasts():
    report = backtest_series(fixture_series(), origins=(2005,), methods=("linear_trend",))
    assert len(report["folds"]) == 2
    for r in report["folds"]:
        assert abs(r["residual"]) < 1e-12
        assert r["parameters"]["slope_per_year"] == pytest.approx(0.2)
        assert r["interval_n"] > 0
        assert r["lower"] is not None
        assert r["roles"]["holdout"] == [r["target_year"]]
        assert max(r["training_years"]) == r["origin"]


def test_future_mutation_cannot_change_fit_or_intervals():
    s = fixture_series()
    first = backtest_series(s, origins=(2000,))
    for r in s["observations"]:
        if r["year"] > 2000:
            r["value"] *= 100
    second = backtest_series(s, origins=(2000,))
    for a, b in zip(first["folds"], second["folds"], strict=True):
        for key in ("predicted", "lower", "upper", "parameters", "interval_validation", "roles"):
            assert a[key] == b[key]
        assert a["observed"] != b["observed"]
        assert all(r["target"] <= a["origin"] for r in a["interval_validation"])


def test_breaks_and_gaps_are_not_bridged():
    s = fixture_series()
    for r in s["observations"]:
        if r["year"] >= 2005:
            r["segment"] = "redesign"
    report = backtest_series(s, origins=(2000, 2005, 2015))
    assert {f["origin"] for f in report["folds"]} == {2015}
    assert {r["reason"] for r in report["skipped"]} >= {
        "comparability boundary or missing year",
        "insufficient comparable annual training",
    }
    s = fixture_series()
    s["observations"] = [r for r in s["observations"] if r["year"] != 2003]
    assert not backtest_series(s, origins=(2000,))["folds"]


def test_interval_insufficient_data_is_null_not_zero():
    r = backtest_series(fixture_series(), origins=(1979,))["folds"]
    assert all(f["lower"] is None and f["upper"] is None for f in r)
    assert metrics(r)["coverage"] is None


def test_interval_uses_rank_and_known_horizon_errors():
    s = fixture_series()
    f = backtest_series(s, origins=(2000,), methods=("persistence",), horizons=(5,))["folds"][0]
    assert f["predicted"] == 16
    assert f["lower"] == pytest.approx(15)
    assert f["upper"] == pytest.approx(17)


def test_metrics_signed_errors_and_zero_denominators():
    rows = [
        {"observed": 0, "residual": -2, "lower": -2, "upper": 2},
        {"observed": 4, "residual": 2, "lower": 0, "upper": 3},
    ]
    assert metrics(rows) == dict(
        n=2, mae=2.0, rmse=2.0, bias=0.0, mape_percent=None, interval_n=2, coverage=0.5
    )
    assert metrics([])["n"] == 0


@pytest.mark.parametrize(
    "kwargs", [{"horizons": (0,)}, {"window": 2}, {"coverage": 1}, {"methods": ("diet",)}]
)
def test_bad_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        backtest_series(fixture_series(), **kwargs)


def test_invalid_forecast_and_observations_rejected():
    s = fixture_series()
    with pytest.raises(ValueError, match="before target"):
        forecast(s["observations"], 1980, "linear_trend")
    s["observations"][0]["value"] = np.nan
    with pytest.raises(ValueError, match="finite"):
        validate_series([s])
    s = fixture_series()
    s["observations"].append(s["observations"][0].copy())
    with pytest.raises(ValueError, match="duplicate"):
        validate_series([s])


def test_bundled_sources_and_known_cells():
    series, manifest = load_history()
    assert len(series) == 13
    s = {s["id"]: s for s in series}
    assert s["e0_both_sexes"]["observations"][0]["value"] == 70.8
    assert s["e0_both_sexes"]["observations"][-1]["value"] == 78.7
    assert s["diabetes_crude"]["observations"][0]["value"] == 5.9
    assert s["sweetener_availability"]["observations"][0]["value"] == 119.1496425
    assert all(len(r["sha256"]) == 64 for r in manifest["sources"].values())


def test_bundle_corruption_rejected(tmp_path):
    from demeter.data.ingest import BUNDLE

    for name in ("historical.json", "historical_manifest.json"):
        (tmp_path / name).write_bytes((BUNDLE / name).read_bytes())
    with (tmp_path / "historical.json").open("ab") as f:
        f.write(b" ")
    with pytest.raises(ValueError, match="checksum"):
        load_history(tmp_path)


def test_raw_checksum_drift_fails_before_writing(tmp_path):
    from demeter.data.ingest import BUNDLE

    dest = tmp_path / "derived"
    raw = tmp_path / "raw"
    dest.mkdir()
    raw.mkdir()
    (dest / "historical_manifest.json").write_bytes(
        (BUNDLE / "historical_manifest.json").read_bytes()
    )
    (raw / "nchs_life_expectancy.csv").write_text("changed source")
    with pytest.raises(ValueError, match="checksum"):
        rebuild_history(raw, dest)
    assert not (dest / "historical.json").exists()


def test_cli_and_run_provenance(tmp_path):
    out = tmp_path / "history.json"
    r = CliRunner().invoke(app, ["historical-backtest", "--origin", "2000", "--output", str(out)])
    assert r.exit_code == 0, r.output
    report = json.loads(out.read_text())
    assert not report["scientific_validation_of_diet"]
    assert not report["integrated_health_model_validated"]
    assert report["metadata"]["evidence_sha256"]
    assert report["metadata"]["python_source_sha256"]
    assert report["configuration"]["origins"] == [2000]
    assert len(report["series"]) == 13


def test_real_history_preserves_breaks_and_finite_json():
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    result = historical_backtest(registry)
    json.dumps(result, allow_nan=False)
    for s in result["series"]:
        for f in s["folds"]:
            assert max(f["roles"]["calibration"]) < min(f["roles"]["holdout"])
            if s["domain"] == "diabetes":
                assert not f["origin"] < 2019 <= f["target_year"]
    # Loading/backtesting must not overwrite the pinned source values.
    a, _ = load_history()
    b = copy.deepcopy(a)
    backtest_series(a[0])
    assert a == b
