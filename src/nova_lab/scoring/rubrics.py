"""Explicit score rubrics used by the synthetic market lab."""

PARENT_WEIGHTS = {
    "problem_relevance": 15,
    "product_clarity": 10,
    "child_value": 15,
    "parent_value": 10,
    "trust": 15,
    "differentiation": 10,
    "repeat_use": 10,
    "price_fit": 10,
    "operational_friction": 5,
}


def parent_product_score(metrics: dict[str, float]) -> float:
    """Calculate the published parent/product score from 0--100 metrics.

    Unspecified measures use a neutral midpoint. Operational friction is the
    sole inverse measure: more friction lowers the resulting score.
    """

    total = 0.0
    for key, weight in PARENT_WEIGHTS.items():
        value = metrics.get(key, 50.0)
        if key == "operational_friction":
            value = 100 - value
        total += value * weight / 100
    return round(total, 2)
