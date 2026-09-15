"""Synthetic 30-day usage scenarios; these are not claims about real children."""

from collections import defaultdict
import random

from pydantic import BaseModel, Field

from nova_lab.child.events import ChildInteractionEvent, summarize_usage_events, validate_event_links
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
            aggregates = summarize_usage_events(period_events)
            # Scale the existing novelty assumptions by executed useful events per
            # scheduled situation. This is a design heuristic, not usage prediction.
            snapshot.useful_interactions = round(
                snapshot.useful_interactions * min(
                    1, sum(event.useful for event in period_events) / aggregates["scenario_count"],
                ), 2,
            )
            for field, value in aggregates.items():
                setattr(snapshot, field, value)
    return snapshots


def validate_usage_events(events, usage, children, variants, experiment_variants, seed):
    """Reconcile saved usage with events and the completed run's model inputs."""
    by_variant = {variant.variant_id: variant for variant in variants}
    required_variants = {variant_id for ids in experiment_variants.values() for variant_id in ids}
    if len(by_variant) != len(variants) or set(by_variant) != required_variants:
        raise ValueError("usage variant provenance does not match persisted experiments")
    by_child = {child.persona_id: child for child in children}
    validate_event_links(events, usage, set(by_child), experiment_variants)
    by_session = defaultdict(list)
    for event in events:
        by_session[(event.experiment_id, event.persona_id, event.variant_id)].append(event)
    expected = {}
    for key, rows in by_session.items():
        _, child_id, variant_id = key
        for snapshot in simulate_usage(by_child[child_id], by_variant[variant_id], seed, events=rows):
            expected[(*key, snapshot.period)] = snapshot.useful_interactions
    for snapshot in usage:
        key = tuple(snapshot[field] for field in ("experiment_id", "persona_id", "variant_id", "period"))
        if snapshot["useful_interactions"] != expected[key]:
            raise ValueError(
                f"usage event summary mismatch: run={snapshot['run_id']} "
                f"persona={snapshot['persona_id']} experiment={snapshot['experiment_id']} "
                f"variant={snapshot['variant_id']} period={snapshot['period']} field=useful_interactions"
            )
