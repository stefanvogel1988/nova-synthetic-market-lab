"""State and timeline helpers for synthetic child-use scenarios."""

from pydantic import BaseModel, Field

from nova_lab.child.questions import ChildQuestion


class ChildSessionState(BaseModel):
    """A bounded, simulated interaction state; it does not describe real behavior."""

    interest: float = Field(ge=0, le=1)
    frustration: float = Field(ge=0, le=1)
    mode: str
    needs_parent: bool = False


_NOVELTY_BY_PERIOD = {
    "day_1": 1.00,
    "day_3": 0.82,
    "week_1": 0.70,
    "week_2": 0.58,
    "week_4": 0.50,
}


def novelty_multiplier(period: str) -> float:
    """Return the synthetic novelty assumption for a named checkpoint."""
    return _NOVELTY_BY_PERIOD[period]


def advance_session(state: ChildSessionState, question: ChildQuestion) -> ChildSessionState:
    """Advance a synthetic session by one question event."""
    if question.kind == "follow_up":
        return ChildSessionState(
            interest=min(1.0, state.interest + 0.25),
            frustration=max(0.0, state.frustration - 0.15),
            mode="engaged",
            needs_parent=False,
        )
    if question.kind == "help":
        return ChildSessionState(
            interest=max(0.0, state.interest - 0.1),
            frustration=min(1.0, state.frustration + 0.2),
            mode="needs_help",
            needs_parent=True,
        )
    return ChildSessionState(
        interest=min(1.0, state.interest + 0.1),
        frustration=state.frustration,
        mode="engaged",
        needs_parent=False,
    )
