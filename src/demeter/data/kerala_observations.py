"""Private source-native Kerala observations, with no biological state or time fit.

I-11/I-12 -> F-08 -> T-05/T-08. These objects deliberately have no record serializer
or descriptive repr. Only the protocol-approved aggregate diagnostics are public.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


LABELS = ("Baseline", "12 months", "24 months")
INVALID_KEYS = {"absent", "empty", "formula_unsupported", "error", "unsupported"}


@dataclass(frozen=True, repr=False)
class SourceCode:
    token: str
    literal: str | None


@dataclass(frozen=True, repr=False)
class NominalSourceVisit:
    index: int
    label: str
    glycemia: SourceCode
    ada_diabetes: SourceCode
    incidence_flag: SourceCode
    medication_flags: tuple[SourceCode, ...]
    fasting_storage: str
    two_hour_storage: str
    seen_positive_suffix_evidence: bool
    prior_ada_positive_evidence: bool
    exact_time: None = None
    clinical_confirmation: None = None
    death_status: None = None
    absence_reason: None = None


@dataclass(frozen=True, repr=False)
class SourceSubject:
    opaque_key: tuple
    opaque_cluster: tuple
    assignment: str
    visits: tuple[NominalSourceVisit, ...]
    horizon_total: SourceCode
    prior_clinical_history: None = None
    first_onset_interval: None = None
    death_time: None = None
    contact_time: None = None


def _code(cell, allowed) -> SourceCode:
    kind, value = cell
    literal = value if kind == "string" and value in allowed else None
    token = (
        f"string:{literal}"
        if literal is not None
        else ("string:uninterpreted_text" if kind == "string" else f"{kind}:uninterpreted")
    )
    return SourceCode(token, literal)


def _storage(cell) -> str:
    # Numeric storage is not a performed, valid or clinically interpretable assay.
    return "numeric_cell_present" if cell[0] == "number" else f"{cell[0]}:uninterpreted"


def _group(rows):
    result = {}
    for row in rows:
        key = row["participant_id"]
        if key[0] in INVALID_KEYS or key[1] is None:
            raise ValueError("Source linkage has an invalid typed key")
        result.setdefault(key, []).append(row)
    return result


def build_source_observations(primary_rows, secondary_rows) -> tuple[SourceSubject, ...]:
    """Adapt selected private cells; fail closed on linkage or assignment disagreement.

    Source-cell kinds and opaque keys remain typed. Clinical labels are retained
    literally; unfamiliar labels remain uninterpreted. Nominal labels are not dates.
    """
    primary, secondary = _group(primary_rows), _group(secondary_rows)
    if set(primary) != set(secondary) or any(len(v) != 1 for v in primary.values()):
        raise ValueError("Source subject linkage is missing or nonunique")
    subjects = []
    for key, records in primary.items():
        wide = records[0]
        long = {}
        for row in secondary[key]:
            slot = row["timepoint"]
            if slot not in {("string", value) for value in LABELS} or slot in long:
                raise ValueError("Source nominal visit linkage is invalid or nonunique")
            long[slot] = row
        if set(long) != {("string", value) for value in LABELS}:
            raise ValueError("Source nominal visit slots are incomplete")
        if wide["arms0"] not in {("string", "Control"), ("string", "Intervention")}:
            raise ValueError("Source assignment label is uninterpretable")
        if wide["cluster0"][0] in INVALID_KEYS or wide["cluster0"][1] is None:
            raise ValueError("Source cluster linkage is invalid")
        visits = []
        seen = False
        earlier_ada = False
        for index, label in enumerate(LABELS):
            row = long[("string", label)]
            for stem in ("arms", "cluster"):
                if wide[f"{stem}{index}"] != wide[f"{stem}0"] or row[stem] != wide[f"{stem}0"]:
                    raise ValueError("Source assignment or cluster drift")
            for stem in ("glycemiaADA", "diabADA", "fpgmgdl", "twohrpgmgdl"):
                if row[stem] != wide[f"{stem}{index}"]:
                    raise ValueError("Source clinical copies disagree")
            glycemia = _code(row["glycemiaADA"], {"NGT", "IFG", "IGT", "diabetes"})
            ada = _code(row["diabADA"], {"Yes", "No"})
            incidence = _code(
                wide[f"tot_diab_incidence{index}"] if index else ("absent", None),
                {"Yes", "No"},
            )
            seen = seen or incidence.literal == "Yes"
            drugs = ("diabdrugs_10", "diabdrugs_20") if not index else (f"diabdrugs_{index}",)
            visits.append(
                NominalSourceVisit(
                    index,
                    label,
                    glycemia,
                    ada,
                    incidence,
                    tuple(_code(wide[field], {"Yes", "No"}) for field in drugs),
                    _storage(row["fpgmgdl"]),
                    _storage(row["twohrpgmgdl"]),
                    seen,
                    earlier_ada,
                )
            )
            earlier_ada = earlier_ada or glycemia.literal == "diabetes" or ada.literal == "Yes"
        subjects.append(
            SourceSubject(
                key,
                wide["cluster0"],
                wide["arms0"][1],
                tuple(visits),
                _code(wide["tot_diab_incidence"], {"Yes", "No"}),
            )
        )
    return tuple(subjects)


def public_diagnostics(subjects: tuple[SourceSubject, ...]) -> dict:
    """Only one-way marginals, approved scalar algebra, booleans and unlabeled sizes.

    No keys, clusters, assay values, individual paths, subgroup trajectories or
    labeled joint cells are returned. Counts describe stored records, not rates.
    """
    margins = {}
    for index, label in enumerate(LABELS):
        visits = [subject.visits[index] for subject in subjects]
        margins[label] = {
            field: dict(sorted(Counter(getattr(visit, field).token for visit in visits).items()))
            for field in ("glycemia", "ada_diabetes", "incidence_flag")
        }
        for field in ("fasting_storage", "two_hour_storage"):
            margins[label][field] = dict(
                sorted(Counter(getattr(visit, field) for visit in visits).items())
            )
        margins[label]["medication_flags"] = [
            dict(sorted(Counter(visit.medication_flags[column].token for visit in visits).items()))
            for column in range(2 if index == 0 else 1)
        ]
    algebra = Counter(
        {
            key: 0
            for key in (
                "fully_interpretable_triples",
                "suffix_positive_union",
                "suffix_positive_overlap",
                "total_negative_with_positive_suffix",
                "total_positive_with_both_suffixes_negative",
                "unknown_total_with_positive_suffix",
            )
        }
    )
    category_agreement = True
    omission_compatible = True
    category_evaluated = omission_evaluated = False
    patterns = Counter()
    for subject in subjects:
        first, second = (subject.visits[index].incidence_flag.literal for index in (1, 2))
        total = subject.horizon_total.literal
        positive = first == "Yes" or second == "Yes"
        algebra["fully_interpretable_triples"] += all(v is not None for v in (first, second, total))
        algebra["suffix_positive_union"] += positive
        algebra["suffix_positive_overlap"] += first == second == "Yes"
        algebra["total_negative_with_positive_suffix"] += total == "No" and positive
        algebra["total_positive_with_both_suffixes_negative"] += (
            total == "Yes" and first == second == "No"
        )
        algebra["unknown_total_with_positive_suffix"] += total is None and positive
        for visit in subject.visits:
            if visit.glycemia.literal is not None and visit.ada_diabetes.literal is not None:
                category_evaluated = True
                category_agreement &= (visit.glycemia.literal == "diabetes") == (
                    visit.ada_diabetes.literal == "Yes"
                )
        first_visit, second_visit = subject.visits[1:]
        if first_visit.glycemia.literal == "diabetes" or first_visit.ada_diabetes.literal == "Yes":
            omission_evaluated = True
            omission_compatible &= second_visit.two_hour_storage in {
                "absent:uninterpreted",
                "empty:uninterpreted",
            }
        pattern = tuple(
            (
                v.glycemia.token,
                v.ada_diabetes.token,
                v.incidence_flag.token,
                tuple(flag.token for flag in v.medication_flags),
                v.fasting_storage,
                v.two_hour_storage,
            )
            for v in subject.visits
        ) + (subject.horizon_total.token,)
        patterns[pattern] += 1
    return {
        "subjects": len(subjects),
        "nominal_rows": len(subjects) * len(LABELS),
        "assignment_marginal": dict(sorted(Counter(s.assignment for s in subjects).items())),
        "horizon_total_marginal": dict(
            sorted(Counter(s.horizon_total.token for s in subjects).items())
        ),
        "visit_marginals": margins,
        "incidence_flag_algebra": dict(algebra),
        "ada_category_and_flag_agree_where_both_interpretable": (
            bool(category_agreement) if category_evaluated else None
        ),
        "later_two_hour_storage_absent_after_earlier_ada_positive_compatible": (
            bool(omission_compatible) if omission_evaluated else None
        ),
        "unlabeled_observation_pattern_cell_size_histogram": dict(
            sorted(Counter(patterns.values()).items())
        ),
        "individual_death_contact_confirmation_and_first_onset_unknown": True,
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "independent_validation_allowed": False,
        "scientific_release_ready": False,
    }
