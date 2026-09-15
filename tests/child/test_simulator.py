from nova_lab.child.questions import ChildQuestion
from nova_lab.child.simulator import ChildSessionState, advance_session, novelty_multiplier


def test_novelty_decays_over_30_day_horizon():
    assert novelty_multiplier("day_1") > novelty_multiplier("week_2")
    assert novelty_multiplier("week_2") >= novelty_multiplier("week_4")


def test_follow_up_question_spontaneously_reengages_a_disengaged_session():
    state = ChildSessionState(
        interest=0.2,
        frustration=0.4,
        mode="disengaged",
        needs_parent=False,
    )

    next_state = advance_session(
        state,
        ChildQuestion(prompt="Why do stars twinkle?", kind="follow_up"),
    )

    assert next_state.mode == "engaged"
    assert next_state.interest > state.interest
    assert next_state.frustration < state.frustration
    assert next_state.needs_parent is False
