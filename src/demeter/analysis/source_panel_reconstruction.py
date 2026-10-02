"""Exact source-panel accounting under a caller-declared subset identity.

Repeated assay panels describe the same people. Source disposition slots are not
latent clinical states, and an unrepresented baseline margin supplies no event
history, vital status, or observation time. Design trace: I-11/I-12 -> F-08 -> T-08.
"""

from __future__ import annotations

from fractions import Fraction

from demeter.analysis.endpoint_bounds import _count, _rational

BASELINE_ROWS = ("normal", "prediabetes")
RECORDED_SLOTS = ("normal", "prediabetes", "total_diabetes", "mortality")
UNREPRESENTED_SLOT = "unrepresented_baseline_margin"


def _mapping(value, name: str) -> dict:
    if type(value) is not dict:
        raise ValueError(f"{name} must be a dictionary")
    return value


def _fraction(count: int, denominator: int) -> dict | None:
    return None if denominator == 0 else _rational(Fraction(count, denominator))


def reconstruct_source_panels(
    original_count: int,
    original_prediabetes_counts: dict[str, int],
    selected_panels: dict[str, dict[str, dict[str, int]]],
    *,
    source_subset_identity_declared: bool,
) -> dict:
    """Reconstruct only baseline residuals, conditional on supplied source identity.

    Each assay has exhaustive normal/prediabetes baseline rows and four exhaustive
    recorded disposition slots within its selected rows. The original baseline
    prediabetes margins and the same original/selected population are premises,
    not facts verified by arithmetic. Selected cohort sizes must agree across
    assays; their outcome margins need not agree. No panels are pooled as people.

    Five-slot original-row fractions sum to one, including unrepresented records.
    Selected-row fractions use only the four recorded slots. Their unrepresented
    entry is null because it lies outside that denominator, not because unknown
    outcomes were observed absent. All zero-denominator fractions remain null.
    """
    if type(source_subset_identity_declared) is not bool or not source_subset_identity_declared:
        raise ValueError("Source subset identity must be explicitly declared True")
    original_count = _count(original_count, "original cohort count")
    margins = _mapping(original_prediabetes_counts, "Original assay margins")
    supplied = _mapping(selected_panels, "Selected assay panels")
    if not margins or set(margins) != set(supplied):
        raise ValueError("Original and selected assay inventories must match and be nonempty")
    if any(type(key) is not str or not key or key != key.strip() for key in margins):
        raise ValueError("Assay labels must be nonempty named strings")

    panels = {}
    selected_count = None
    for assay in sorted(margins):
        original_prediabetes = _count(margins[assay], "Original prediabetes count")
        if original_prediabetes > original_count:
            raise ValueError("Original prediabetes count cannot exceed original cohort count")
        originals = {
            "normal": original_count - original_prediabetes,
            "prediabetes": original_prediabetes,
        }
        rows = _mapping(supplied[assay], "Selected baseline rows")
        if set(rows) != set(BASELINE_ROWS):
            raise ValueError("Each assay must supply exhaustive normal/prediabetes baseline rows")
        reconstructed = {}
        panel_selected_count = 0
        for label in BASELINE_ROWS:
            row = _mapping(rows[label], "Selected source row")
            if set(row) != {"baseline_count", *RECORDED_SLOTS}:
                raise ValueError("Selected row must contain exactly its baseline and four slots")
            baseline = _count(row["baseline_count"], "Selected baseline count")
            recorded = {slot: _count(row[slot], "Recorded source count") for slot in RECORDED_SLOTS}
            if sum(recorded.values()) != baseline:
                raise ValueError("Recorded source slots must conserve their selected baseline row")
            original = originals[label]
            if baseline > original:
                raise ValueError("A selected baseline row cannot exceed its original row")
            residual = original - baseline
            partition = {**recorded, UNREPRESENTED_SLOT: residual}
            reconstructed[label] = {
                "original_baseline_count": original,
                "selected_baseline_count": baseline,
                "source_partition_counts": partition,
                "original_row_fraction_denominator": original,
                "original_row_fractions": {
                    slot: _fraction(value, original) for slot, value in partition.items()
                },
                "selected_row_fraction_denominator": baseline,
                "selected_row_fractions": {
                    **{slot: _fraction(value, baseline) for slot, value in recorded.items()},
                    UNREPRESENTED_SLOT: None,
                },
            }
            panel_selected_count += baseline
        if selected_count is not None and panel_selected_count != selected_count:
            raise ValueError("Assay panels must describe the same selected cohort count")
        selected_count = panel_selected_count
        panels[assay] = {"rows": reconstructed}

    return {
        "counts": {
            "original_unique_people": original_count,
            "selected_unique_people": selected_count,
            "unrepresented_baseline_margin": original_count - selected_count,
        },
        "panels": panels,
        "interpretation": {
            "scope": "Conditional reconstruction of supplied source-record partitions",
            "source_subset_identity_declared": True,
            "independently_verified_participant_subset_identity": False,
            "baseline_categories_exhaustive_within_each_assay": True,
            "panels_share_population": True,
            "panels_are_independent_samples": False,
            "cross_assay_joint_followup_identified": False,
            "unrepresented_fraction_within_selected_denominator": "Not applicable; null",
            "residual_is_observed_followup_category": False,
            "residual_vital_status_identified": False,
            "residual_is_wholly_untraced": False,
            "mortality_priority_identified": False,
            "diagnosis_before_death_identified": False,
            "common_elapsed_horizon_assumed": False,
            "exact_event_times_identified": False,
            "source_labels_are_latent_clinical_states": False,
            "sampling_interval": None,
            "stochastic_or_clinical_fit_performed": False,
        },
    }
