from dataclasses import dataclass

from nova_lab.scoring.aggregate import summarize_by_segment
from nova_lab.scoring.bias import (
    apply_positivity_penalty,
    detect_preference_decision_contradiction,
)
from nova_lab.scoring.rubrics import parent_product_score


def test_parent_score_uses_declared_weights():
    metrics = {
        "problem_relevance": 100,
        "product_clarity": 100,
        "child_value": 100,
        "parent_value": 100,
        "trust": 100,
        "differentiation": 100,
        "repeat_use": 100,
        "price_fit": 100,
        "operational_friction": 0,
    }

    assert parent_product_score(metrics) == 100


def test_parent_score_inverts_operational_friction_and_defaults_missing_metrics():
    assert parent_product_score({"operational_friction": 100}) == 47.5


def test_positive_claim_with_rejection_is_penalized():
    assert apply_positivity_penalty(80, ["would_not_buy"]) < 80
    assert detect_preference_decision_contradiction(85, False) is True


def test_only_recognized_objections_reduce_the_score():
    assert apply_positivity_penalty(80, ["would_not_buy", "would_not_buy", "other"]) == 64


@dataclass
class Observation:
    persona_id: str
    metrics: dict[str, float]


def test_segment_summary_reports_each_segment_median_without_flattening_disagreement():
    observations = [
        Observation("p1", {"purchase_interest": 90}),
        Observation("p2", {"purchase_interest": 10}),
        Observation("e1", {"purchase_interest": 40}),
    ]

    summary = summarize_by_segment(
        observations,
        {"p1": "parents", "p2": "parents", "e1": "education"},
    )

    assert summary == {
        "parents": {"n": 2, "median_purchase_interest": 50.0},
        "education": {"n": 1, "median_purchase_interest": 40.0},
    }
