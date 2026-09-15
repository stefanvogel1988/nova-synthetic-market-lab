"""Deterministic synthetic focus-group score updates.

The results model simulated positions only; it makes no claim about the
behavior of real parents or participants.
"""

from pydantic import BaseModel


class FocusGroupResult(BaseModel):
    """Synthetic positions before and after deterministic critiques."""

    initial_scores: dict[str, float]
    final_scores: dict[str, float]


def run_focus_group(
    initial_positions: dict[str, float], critique_effects: dict[str, float]
) -> FocusGroupResult:
    """Apply deterministic critique effects while retaining both score snapshots."""
    final_scores = {
        persona_id: max(0, min(100, score + critique_effects.get(persona_id, 0)))
        for persona_id, score in initial_positions.items()
    }
    return FocusGroupResult(
        initial_scores=initial_positions,
        final_scores=final_scores,
    )
