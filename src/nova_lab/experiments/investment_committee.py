"""Deterministic synthetic investment-committee deliberation.

These score changes model a local simulation and do not describe real investor
behavior or investment decisions.
"""

from pydantic import BaseModel


class InvestmentCommitteeResult(BaseModel):
    """Synthetic member scores before and after peer critique."""

    pre_scores: dict[str, float]
    post_scores: dict[str, float]


def deliberate(
    pre_scores: dict[str, float], peer_adjustments: dict[str, float]
) -> InvestmentCommitteeResult:
    """Apply deterministic peer adjustments and preserve pre/post snapshots."""
    post_scores = {
        member_id: max(0, min(100, score + peer_adjustments.get(member_id, 0)))
        for member_id, score in pre_scores.items()
    }
    return InvestmentCommitteeResult(pre_scores=pre_scores, post_scores=post_scores)
