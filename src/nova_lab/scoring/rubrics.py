"""Explicit score rubrics used by the synthetic market lab."""

from math import isfinite

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


def validate_parent_metrics(metrics: dict[str, float]) -> None:
    """Require complete 0--100 components and a valid score when supplied."""
    missing = PARENT_WEIGHTS.keys() - metrics.keys()
    if missing:
        raise ValueError(f"missing mandatory parent/product rubric components: {', '.join(sorted(missing))}")
    for key in (*PARENT_WEIGHTS, "parent_product_score"):
        if key in metrics and (not isfinite(metrics[key]) or not 0 <= metrics[key] <= 100):
            raise ValueError(f"parent/product rubric {key} must be finite and between 0 and 100")


def parent_product_score(metrics: dict[str, float]) -> float:
    """Calculate the published parent/product score from 0--100 metrics.

    Every weighted component must be explicit; missing values are not evidence
    for a neutral score. Operational friction is the sole inverse measure.
    """
    validate_parent_metrics(metrics)
    total = 0.0
    for key, weight in PARENT_WEIGHTS.items():
        value = metrics[key]
        if key == "operational_friction":
            value = 100 - value
        total += value * weight / 100
    return round(total, 2)
