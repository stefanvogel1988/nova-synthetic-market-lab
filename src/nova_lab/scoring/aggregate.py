"""Segment-level summaries that retain differences between cohorts."""

from collections import defaultdict
from statistics import median
from typing import Protocol


class _Observation(Protocol):
    persona_id: str
    metrics: dict[str, float]


def summarize_by_segment(
    observations: list[_Observation], segment_map: dict[str, str]
) -> dict[str, dict[str, float | int]]:
    """Return count and median purchase interest for every represented segment."""

    buckets: dict[str, list[float]] = defaultdict(list)
    for observation in observations:
        buckets[segment_map[observation.persona_id]].append(
            observation.metrics.get("purchase_interest", 0.0)
        )
    return {
        segment: {"n": len(values), "median_purchase_interest": median(values)}
        for segment, values in buckets.items()
    }
