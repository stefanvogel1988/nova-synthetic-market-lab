import random

from nova_lab.models.experiment import ExperimentObservation
from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant


class DeterministicEngine:
    def __init__(self, seed: int):
        self._seed = seed

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, value)), 2)

    def evaluate_parent(
        self, parent: ParentPersona, variant: ProductVariant, context: dict
    ) -> ExperimentObservation:
        rng = random.Random(
            f"{self._seed}:{parent.persona_id}:{variant.variant_id}:{context}"
        )
        price = float(context.get("price_eur", 179))
        relevance = (
            45 + 25 * parent.education_orientation + (8 if variant.audio_first else 0)
        )
        child_value = (
            40
            + (18 if variant.ai_q_and_a else 0)
            + (10 if variant.curiosity_mode else 0)
        )
        trust = 55 - 28 * parent.privacy_concern * (0 if variant.privacy_first else 1)
        trust += 18 if variant.privacy_first else 0
        ai_penalty = {"enthusiastic": 0, "pragmatic": 4, "cautious": 14, "opposed": 28}[
            parent.ai_attitude
        ]
        trust -= ai_penalty if variant.ai_q_and_a else 0
        price_fit = (
            100
            - max(0, price - parent.disposable_budget_eur) * 0.8
            - parent.price_sensitivity * 20
        )
        noise = rng.uniform(-3, 3)
        metrics = {
            "problem_relevance": self._clamp(relevance + noise),
            "child_value": self._clamp(child_value + noise),
            "parent_value": self._clamp((relevance + child_value) / 2 + noise),
            "trust": self._clamp(trust + noise),
            "price_fit": self._clamp(price_fit + noise),
            "purchase_interest": self._clamp(
                (relevance + child_value + trust + price_fit) / 4 - 5
            ),
        }
        objections = []
        if metrics["trust"] < 45:
            objections.append("privacy_or_ai_trust")
        if metrics["price_fit"] < 45:
            objections.append("price")
        return ExperimentObservation(
            run_id=str(context.get("run_id", "test")),
            experiment_id=str(context.get("experiment_id", "provider-test")),
            persona_id=parent.persona_id,
            variant_id=variant.variant_id,
            metrics=metrics,
            objections=objections,
            rationale="deterministic zero-cost simulation; not real demand",
        )
