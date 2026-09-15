"""Synthetic 30-day usage scenarios; these are not claims about real children."""

import random

from pydantic import BaseModel, Field

from nova_lab.child.simulator import (
    ChildSessionState,
    lapse_session,
    novelty_multiplier,
    spontaneously_reengage,
)
from nova_lab.models.persona import ChildPersona
from nova_lab.models.product import ProductVariant


CHECKPOINTS = ("day_1", "day_3", "week_1", "week_2", "week_4")
_LAPSE_THRESHOLD = 3.1


class UsageSnapshot(BaseModel):
    """A synthetic checkpoint in a scenario, not observed child-use data."""

    period: str
    useful_interactions: float = Field(ge=0)
    frustration: float = Field(ge=0, le=1)
    parent_interventions: float = Field(ge=0)
    mode_mix: dict[str, float]
    session_state: ChildSessionState


def simulate_usage(
    child: ChildPersona, variant: ProductVariant, seed: int
) -> list[UsageSnapshot]:
    """Simulate one deterministic synthetic scenario across the five checkpoints."""
    rng = random.Random(seed)
    base_interactions = 4 + child.curiosity_frequency * 6
    curiosity_bonus = 1.3 if variant.curiosity_mode else 1.0
    frustration = max(0.0, 1 - child.frustration_tolerance) * (
        0.3 if variant.privacy_first else 0.4
    )
    snapshots: list[UsageSnapshot] = []
    session_state = ChildSessionState(
        interest=child.curiosity_frequency,
        frustration=frustration,
        mode="engaged",
    )

    for period in CHECKPOINTS:
        useful = base_interactions * novelty_multiplier(period) * curiosity_bonus
        if useful < _LAPSE_THRESHOLD:
            if session_state.mode == "lapsed":
                reengagement_chance = 0.15 + child.novelty_seeking * 0.4
                session_state = spontaneously_reengage(
                    session_state,
                    triggered=rng.random() < reengagement_chance,
                )
                useful = useful if session_state.mode == "engaged" else 0.0
            else:
                session_state = lapse_session(session_state)
                useful = 0.0
        else:
            session_state = ChildSessionState(
                interest=min(1.0, useful / 10),
                frustration=frustration,
                mode="engaged",
            )
        snapshots.append(
            UsageSnapshot(
                period=period,
                useful_interactions=round(useful, 2),
                frustration=round(frustration, 2),
                parent_interventions=round(frustration * 2, 2),
                mode_mix={
                    "music": child.preference_music,
                    "stories": child.preference_stories,
                    "learning": child.preference_learning,
                },
                session_state=session_state,
            )
        )
    return snapshots
