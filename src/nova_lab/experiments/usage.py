"""Synthetic 30-day usage scenarios; these are not claims about real children."""

import random
from collections import Counter
from statistics import mean

from pydantic import BaseModel, Field

from nova_lab.child.events import ChildInteractionEvent
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
    event_ids: list[str] = Field(default_factory=list)
    scenario_count: int = Field(default=0, ge=0)
    self_initiated_interactions: int = Field(default=0, ge=0)
    abandonment_reasons: dict[str, int] = Field(default_factory=dict)


def simulate_usage(
    child: ChildPersona, variant: ProductVariant, seed: int, *,
    events: list[ChildInteractionEvent] | None = None,
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
    if events is not None:
        for snapshot in snapshots:
            period_events = [event for event in events if event.period == snapshot.period]
            if not period_events:
                raise ValueError("missing child interaction events for usage checkpoint")
            final_states = {event.scenario_id: event.state_after for event in period_events}
            useful = [event for event in period_events if event.useful]
            # Scale the existing novelty assumptions by executed useful events per
            # scheduled situation. This is a design heuristic, not usage prediction.
            snapshot.useful_interactions = round(
                snapshot.useful_interactions * min(1, len(useful) / len(final_states)), 2,
            )
            snapshot.frustration = round(mean(s.frustration for s in final_states.values()), 2)
            snapshot.parent_interventions = sum(s.needs_parent for s in final_states.values())
            modes = Counter(event.mode for event in useful)
            snapshot.mode_mix = {mode: modes[mode] / max(1, len(useful)) for mode in ("music", "stories", "learning")}
            snapshot.event_ids = [event.event_id for event in period_events]
            snapshot.scenario_count = len(final_states)
            snapshot.self_initiated_interactions = sum(event.self_initiated for event in period_events)
            snapshot.abandonment_reasons = dict(Counter(
                event.abandonment_reason for event in period_events if event.abandonment_reason
            ))
    return snapshots
