"""Controls that expose overly positive synthetic findings."""

_PENALIZED_OBJECTIONS = {"would_not_buy", "privacy_or_ai_trust", "price"}


def detect_preference_decision_contradiction(stated_interest: float, selected: bool) -> bool:
    """Flag high stated interest that did not result in selection."""

    return stated_interest >= 75 and not selected


def apply_positivity_penalty(score: float, objections: list[str]) -> float:
    """Reduce a score for each material objection without going below zero."""

    penalty = 8 * sum(objection in _PENALIZED_OBJECTIONS for objection in objections)
    return round(max(0.0, score - penalty), 2)
