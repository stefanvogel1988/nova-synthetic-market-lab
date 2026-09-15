from nova_lab.experiments.usage import simulate_usage
from nova_lab.models.persona import ChildPersona
from nova_lab.models.product import ProductVariant


def _child(curiosity: float) -> ChildPersona:
    return ChildPersona(
        persona_id="synthetic-child",
        age=7,
        curiosity_frequency=curiosity,
        language_ability=0.7,
        reading_ability=0.6,
        attention_span=0.7,
        willingness_to_speak_to_devices=0.8,
        frustration_tolerance=0.7,
        novelty_seeking=0.7,
        sibling_context="only_child",
        preference_music=0.4,
        preference_stories=0.3,
        preference_learning=0.3,
        preferred_domains=["space"],
    )


def _variant() -> ProductVariant:
    return ProductVariant(
        variant_id="synthetic-variant",
        label="Synthetic variant",
        description="Test-only synthetic scenario",
        audio_first=True,
        ai_q_and_a=True,
        curiosity_mode=True,
        learning_first=False,
        privacy_first=True,
        education_story=False,
    )


def test_usage_returns_the_exact_30_day_checkpoint_timeline():
    snapshots = simulate_usage(_child(0.8), _variant(), seed=11)

    assert [snapshot.period for snapshot in snapshots] == [
        "day_1",
        "day_3",
        "week_1",
        "week_2",
        "week_4",
    ]
    assert snapshots[0].useful_interactions > snapshots[-1].useful_interactions


def test_high_curiosity_is_retained_while_low_curiosity_can_lapse_by_week_four():
    high_curiosity = simulate_usage(_child(0.9), _variant(), seed=7)
    low_curiosity = simulate_usage(_child(0.05), _variant(), seed=7)

    assert high_curiosity[-1].useful_interactions > 0
    assert low_curiosity[-1].useful_interactions == 0


def test_lapsed_session_can_spontaneously_reengage_at_a_later_checkpoint():
    snapshots = simulate_usage(_child(0.0), _variant(), seed=7)

    assert snapshots[3].session_state.mode == "lapsed"
    assert snapshots[3].useful_interactions == 0
    assert snapshots[4].session_state.mode == "engaged"
    assert snapshots[4].useful_interactions > 0


def test_misunderstanding_then_lapse_preserves_required_parent_intervention():
    # A later lapse must not erase an earlier explicit request for adult help.
    from pathlib import Path

    from nova_lab.child.events import DeterministicChildEngine
    from nova_lab.experiments.registry import load_variants
    from nova_lab.personas.factory import PersonaFactory

    child = PersonaFactory(7).make_children(1)[0].model_copy(update={
        "language_ability": 0.1, "attention_span": 0.1,
    })
    variant = load_variants(Path("config/variants.yaml"))["C"]
    events = [event for event in DeterministicChildEngine().simulate(
        child, variant, 7, run_id="regression", experiment_id="usage-v1",
    ) if event.scenario_id == "weak_wifi"]
    day_one = [event for event in events if event.period == "day_1"]
    assert day_one[-3].kind == "misunderstanding"
    assert day_one[-3].state_after.needs_parent is True
    assert day_one[-1].kind == "lapse"
    assert day_one[-1].state_after.needs_parent is False

    snapshots = simulate_usage(child, variant, seed=7, events=events)

    assert snapshots[0].parent_interventions == 1
