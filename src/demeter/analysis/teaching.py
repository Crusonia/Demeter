"""Reviewed prose and deterministic summaries shared by browser and offline exports."""

from __future__ import annotations

import hashlib
import html
from pathlib import Path

CONTENT = Path(__file__).parent / "content/charts.md"


def teaching_content() -> tuple[dict, str]:
    raw = CONTENT.read_bytes()
    records: dict = {}
    record = None
    field = None
    for line in raw.decode("utf-8").splitlines():
        if line.startswith("## "):
            record = records.setdefault(line[3:].strip(), {})
            field = None
        elif line.startswith("### ") and record is not None:
            field = line[4:].strip().lower()
            record[field] = ""
        elif field and line.strip():
            record[field] = (record[field] + " " + line.strip()).strip()
    return records, hashlib.sha256(raw).hexdigest()


def guide_for(name: str, records: dict | None = None) -> dict:
    records = records or teaching_content()[0]
    if name in records:
        return records[name]
    for pattern, guide in records.items():
        if pattern.endswith("*") and pattern != "*" and name.startswith(pattern[:-1]):
            return guide
    return records["*"]


def guide_html(name: str, records: dict | None = None) -> str:
    guide = guide_for(name, records)
    labels = {
        "read": "How to read it",
        "mechanism": "Why it happens in this model",
        "try": "Try an experiment",
        "predict": "Predict before running",
        "challenge": "Challenge an assumption",
        "evidence": "What evidence would change your interpretation?",
        "limit": "What this cannot establish",
    }
    return (
        '<aside class="teaching"><h3>'
        + html.escape(guide["question"])
        + "</h3>"
        + "".join(
            f"<p><strong>{label}.</strong> {html.escape(guide[key])}</p>"
            for key, label in labels.items()
            if key in guide
        )
        + "</aside>"
    )


def summary(payload: dict) -> list[str]:
    sim = payload["simulation"]
    first, last = sim["annual"][0], sim["annual"][-1]
    return [
        f"{sim['scenario']}: model years 0–{sim['years']}. These are nominal model results.",
        f"Living population changes from {sim['starting_population']:,.0f} to "
        f"{sim['ending_population']:,.0f}; cumulative deaths are {sim['cumulative_deaths']:,.0f}. "
        "Births and migration are zero.",
        f"Period life expectancy changes from {first['life_expectancy']:.2f} to "
        f"{last['life_expectancy']:.2f} years within this run. This is not a comparison "
        "with the reference and is not an individual lifespan forecast.",
    ]
