"""Reconstruct observed food exposures; observations do not identify causal effects."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

from demeter.data.ingest import BUNDLE, digest
from demeter.data.nhanes import STORE as NHANES_STORE, encoded, read_xpt, storage_numbers
from demeter.schema import EvidenceRegistry

STORE = Path("data/sources/dietary/2026-09-27")
DATASET = "dietary_baselines"


class Tables(HTMLParser):
    """Read source HTML tables without executing page content or guessing values."""

    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.sup = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "sup":
            self.sup += 1

    def handle_data(self, data):
        if self.cell is not None and not self.sup:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "sup":
            self.sup -= 1
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def extract_upf(path: Path, spec: dict) -> list[dict]:
    parser = Tables()
    parser.feed(path.read_text(encoding="utf-8"))
    tables = parser.tables
    if len(tables) != spec["table_count"]:
        raise ValueError("Unexpected CDC UPF table count")
    result = []
    for index, kind in ((0, "sex"), (1, "age"), (4, "history")):
        table = tables[index]
        if not table or table[0][-2:] != ["Percent", "Standard error"]:
            raise ValueError("Unexpected UPF table columns")
        group = None
        for row in table[1:]:
            if not row:
                continue
            if not any(row[1:]):
                group = row[0]
                continue
            if group != "Adults":
                continue
            if len(row) != 4:
                raise ValueError("Unexpected UPF row")
            label, n, mean, se = row
            period = (
                spec["period_labels"].get(label) if kind == "history" else spec["current_period"]
            )
            if period is None:
                raise ValueError("Unregistered UPF survey period")
            age = spec["age_labels"][label] if kind == "age" else "19_plus"
            sex = (
                {"Total": "all", "Male": "male", "Female": "female"}[label]
                if kind == "sex"
                else "all"
            )
            mean, se, n = float(mean), float(se), int(n.replace(",", ""))
            if not 0 <= mean <= 100 or se < 0 or n <= 0:
                raise ValueError("Invalid published UPF estimate")
            record = {
                "period": period,
                "exposure": "upf",
                "age_group": age,
                "sex": sex,
                "unit": "percent_energy",
                "mean": mean,
                "standard_error": se,
                "n": n,
                "status": "observed",
                "evidence_grade": "C",
                "source_table": index + 1,
                "distribution": None,
                "distribution_note": "Published mean and SE; individual intake distribution not reconstructed",
                "source": spec["source_url"],
                "population": "U.S. civilian noninstitutionalized adults 19+; day-one reliable dietary recall",
                "comparability_break": period == spec["current_period"],
            }
            # Latest total appears in Tables 1 and 5; both must agree.
            old = next(
                (
                    r
                    for r in result
                    if all(r[k] == record[k] for k in ("period", "age_group", "sex"))
                ),
                None,
            )
            if old:
                if any(old[k] != record[k] for k in ("mean", "standard_error", "n")):
                    raise ValueError("Published UPF tables disagree")
            else:
                result.append(record)
    if len(result) != spec["expected_adult_records"]:
        raise ValueError("Missing published UPF records")
    return result


def survey_mean(
    frame: pd.DataFrame, domain: pd.Series, column: str, confidence: float, quantiles: list[float]
) -> dict:
    """Taylor-linearized domain mean; quantiles describe reported days, not usual intake."""
    weight = frame["weight"].to_numpy(dtype=float)
    design = frame[["SDMVSTRA", "SDMVPSU"]]
    values, d = frame[column].to_numpy(dtype=float), domain.to_numpy(dtype=bool)
    if (
        not np.isfinite(weight).all()
        or (weight <= 0).any()
        or not np.isfinite(design.to_numpy()).all()
    ):
        raise ValueError("Invalid dietary survey weights/design")
    if not 0 < confidence < 1 or any(not 0 < q < 1 for q in quantiles):
        raise ValueError("Invalid confidence or quantile level")
    if not np.isfinite(values[d]).all() or (values[d] < 0).any():
        raise ValueError("Invalid observed dietary intake")
    if not d.any():
        return {
            "n": 0,
            "mean": None,
            "standard_error": None,
            "interval": None,
            "distribution": None,
            "status": "empty_domain",
        }
    w = weight / weight.max()
    denominator = float(w[d].sum())
    mean = float(np.dot(w[d], values[d]) / denominator)
    residual = np.zeros(len(frame))
    residual[d] = w[d] * (values[d] - mean) / denominator
    totals = design.assign(residual=residual).groupby(["SDMVSTRA", "SDMVPSU"]).residual.sum()
    variance = 0.0
    for _, v in totals.groupby(level=0):
        if len(v) < 2:
            raise ValueError("Singleton dietary survey stratum")
        variance += len(v) / (len(v) - 1) * float(((v - v.mean()) ** 2).sum())
    domain_design = design.loc[domain].drop_duplicates()
    df = len(domain_design) - domain_design.SDMVSTRA.nunique()
    se = float(np.sqrt(variance))
    interval = None
    if df > 0 and se > 0:
        half = float(t.ppf((1 + confidence) / 2, df)) * se
        interval = {
            "level": confidence,
            "low": max(0.0, mean - half),
            "high": mean + half,
            "method": "Taylor-linearized mean, domain t interval",
        }
    order = np.argsort(values[d], kind="stable")
    x, dw = values[d][order], w[d][order]
    cumulative = np.cumsum(dw) / dw.sum()
    return {
        "n": int(d.sum()),
        "mean": mean,
        "standard_error": se,
        "interval": interval,
        "degrees_of_freedom": int(df),
        "status": "estimated",
        "distribution": {
            "kind": "weighted empirical distribution of single-day reported intake",
            "quantiles": {
                str(q): float(x[min(np.searchsorted(cumulative, q), len(x) - 1)]) for q in quantiles
            },
            "observed_min": float(x[0]),
            "observed_max": float(x[-1]),
        },
    }


def rebuild_dietary(
    registry: EvidenceRegistry, source: Path = STORE, destination: Path = BUNDLE
) -> dict:
    spec = registry.datasets[DATASET]
    if spec["model_role"] != "exposure_reference_only":
        raise ValueError("Invalid dietary source role")
    receipt = json.loads((source / "manifest.json").read_bytes())
    required = {"db536.htm"}
    for cycle in spec["cycles"]:
        required.add(cycle["dietary_file"])
        if cycle["demographics_store"] == "dietary":
            required.add(cycle["demographics_file"])
    if set(receipt["sources"]) != required:
        raise ValueError("Unexpected dietary source manifest")
    for name, record in receipt["sources"].items():
        if Path(name).name != name:
            raise ValueError("Invalid dietary source filename")
        if digest((source / name).read_bytes()) != record["sha256"]:
            raise ValueError(f"Dietary source checksum mismatch: {name}")
    # Reuse the pinned demographics without copying or altering the earlier source store.
    nhanes_receipt = json.loads((NHANES_STORE / "manifest.json").read_bytes())["sources"][
        "P_DEMO.xpt"
    ]
    if digest((NHANES_STORE / "P_DEMO.xpt").read_bytes()) != nhanes_receipt["sha256"]:
        raise ValueError("Dietary demographics checksum mismatch")
    rows = extract_upf(source / "db536.htm", spec["upf"])
    a = spec["analysis"]
    columns = [v["column"] for v in a["nutrients"].values()]
    correlations = []
    for cycle in spec["cycles"]:
        demo_root = source if cycle["demographics_store"] == "dietary" else NHANES_STORE
        demo = read_xpt(
            demo_root / cycle["demographics_file"], ["RIAGENDR", "RIDAGEYR", "SDMVSTRA", "SDMVPSU"]
        )
        dietary = read_xpt(source / cycle["dietary_file"], [cycle["weight"], "DR1DRSTZ", *columns])
        frame = demo.merge(dietary, on="SEQN", how="left", validate="one_to_one").rename(
            columns={cycle["weight"]: "weight"}
        )
        if (frame.weight.dropna() < 0).any():
            raise ValueError("Negative dietary weight")
        frame = frame.loc[frame.weight > 0].copy()
        if frame.RIDAGEYR.isna().any() or not frame.RIAGENDR.isin([1, 2]).all():
            raise ValueError("Invalid dietary age/sex data")
        complete = (
            (frame.DR1DRSTZ == a["reliable_recall_code"])
            & np.isfinite(frame[columns]).all(axis=1)
            & (frame[columns] >= 0).all(axis=1)
            & (frame.DR1TKCAL > 0)
        )
        for age in a["age_groups"]:
            for sex, code in (("all", None), ("male", 1), ("female", 2)):
                domain = frame.RIDAGEYR >= age["min"]
                if age["max"] is not None:
                    domain &= frame.RIDAGEYR <= age["max"]
                if code is not None:
                    domain &= frame.RIAGENDR == code
                valid = domain & complete
                denom = float(frame.loc[domain, "weight"].sum())
                for key, nutrient in a["nutrients"].items():
                    rows.append(
                        {
                            "period": cycle["id"],
                            "exposure": key,
                            "age_group": age["id"],
                            "sex": sex,
                            "unit": nutrient["unit"],
                            **survey_mean(
                                frame,
                                valid,
                                nutrient["column"],
                                a["confidence_level"],
                                a["quantiles"],
                            ),
                            "missing_weight_fraction": float(
                                frame.loc[domain & ~complete, "weight"].sum()
                            )
                            / denom
                            if denom
                            else None,
                            "source": receipt["sources"][cycle["dietary_file"]]["url"],
                            "population": spec["population"],
                            "evidence_grade": "C",
                            "comparability_break": cycle["mode_change"],
                        }
                    )
                if age["id"] == "20_plus" and sex == "all" and valid.any():
                    x = frame.loc[valid, columns].to_numpy()
                    w = frame.loc[valid, "weight"].to_numpy()
                    centered = x - np.average(x, axis=0, weights=w)
                    cov = (centered.T * w) @ centered / w.sum()
                    scale = np.sqrt(np.diag(cov))
                    corr = np.divide(
                        cov,
                        scale[:, None] * scale[None, :],
                        out=np.full_like(cov, np.nan),
                        where=(scale[:, None] * scale[None, :]) > 0,
                    )
                    correlations.append(
                        {
                            "period": cycle["id"],
                            "exposures": list(a["nutrients"]),
                            "matrix": [
                                [float(v) if np.isfinite(v) else None for v in row] for row in corr
                            ],
                            "scope": "Descriptive weighted same-day correlation; not causal or a parameter covariance",
                        }
                    )
    report = {
        "schema_version": 1,
        "model_role": "exposure_reference_only",
        "scientific_release_ready": False,
        "rows": rows,
        "correlations": correlations,
        "limitations": spec["limitations"],
        "provenance": {
            "definition_sha256": digest(encoded(spec)),
            "sources": receipt["sources"],
            "reused_demographics": nhanes_receipt,
            "transform": "demeter.data.dietary.rebuild_dietary",
            "transform_version": 1,
        },
    }
    content = encoded(storage_numbers(report))
    manifest = {
        "schema_version": 1,
        "bundle_sha256": digest(content),
        "definition_sha256": digest(encoded(spec)),
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "dietary_baselines.json").write_bytes(content)
    (destination / "dietary_manifest.json").write_bytes(encoded(manifest))
    return manifest


def load_dietary(registry: EvidenceRegistry, bundle: Path = BUNDLE) -> dict:
    content = (bundle / "dietary_baselines.json").read_bytes()
    manifest = json.loads((bundle / "dietary_manifest.json").read_bytes())
    if (
        digest(content) != manifest["bundle_sha256"]
        or digest(encoded(registry.datasets[DATASET])) != manifest["definition_sha256"]
    ):
        raise ValueError("Dietary bundle or definition checksum mismatch")
    report = json.loads(content)
    if (
        report["schema_version"] != 1
        or manifest["schema_version"] != 1
        or report["provenance"]["definition_sha256"] != manifest["definition_sha256"]
        or report["model_role"] != "exposure_reference_only"
        or report["scientific_release_ready"]
    ):
        raise ValueError("Invalid dietary bundle role")
    return report


def reference_value(report: dict, exposure: str, period: str, sex: str) -> dict:
    age = "19_plus" if exposure == "upf" else "20_plus"
    rows = [
        r
        for r in report["rows"]
        if (r["exposure"], r["period"], r["sex"], r["age_group"]) == (exposure, period, sex, age)
    ]
    if len(rows) != 1 or rows[0]["mean"] is None:
        raise ValueError(f"No unique supported dietary reference for {exposure}/{period}/{sex}")
    return rows[0]
