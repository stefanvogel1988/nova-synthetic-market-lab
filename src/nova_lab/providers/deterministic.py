import random
import json

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
        # Common noise within paired comparisons; labels and experimental options
        # must not masquerade as causal effects by changing random draws.
        features = variant.model_dump(exclude={"variant_id", "label", "description"})
        rng = random.Random(f"{self._seed}:{parent.persona_id}:{json.dumps(features, sort_keys=True)}")
        price = float(context.get("price_eur", 179))
        subscription = float(context.get("subscription_eur", 0))
        assumptions = []
        clarity, friction = 60.0, 0.0
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
        if "positioning" in context:
            framing = context["positioning"]
            clarity, trust_change = {
                "AI music box for children": (50, 8 if parent.ai_attitude == "enthusiastic" else -ai_penalty),
                "screen-free audio and knowledge box": (65, 4),
                "music, stories and knowledge without a screen": (70, 2),
                "screen-free curiosity companion": (55, 6 * parent.education_orientation),
            }[framing]
            trust += trust_change
            assumptions.append(f"positioning={framing}: assumed clarity={clarity}, trust adjustment={trust_change:.2f}")
        if "privacy_mode" in context:
            mode = context["privacy_mode"]
            risk, control, effort = {
                "always_on": (1.0, 0, 0),
                "push_to_talk": (0.4, 8, 8),
                "push_to_talk_kill_switch": (0.1, 14, 14),
            }[mode]
            # Explicit microphone design replaces the variant's default privacy design.
            trust = 55 - 28 * parent.privacy_concern * risk + control * parent.privacy_concern
            trust -= ai_penalty if variant.ai_q_and_a else 0
            friction += effort * parent.convenience_orientation
            assumptions.append(f"privacy_mode={mode}: assumed risk multiplier={risk}, control bonus={control} times privacy concern, effort={effort} times convenience orientation")
        if "learning_design" in context:
            design = context["learning_design"]
            gain, effort = {"direct": (0, 0), "follow_up": (10, 12), "exploration": (20, 28)}[design]
            child_value += gain * parent.education_orientation
            friction += effort * parent.convenience_orientation
            assumptions.append(f"learning_design={design}: assumed value gain={gain} times education orientation, effort={effort} times convenience orientation")
        commitment = price + 3 * subscription
        subscription_penalty = subscription * (1 - parent.subscription_tolerance) * 3
        price_fit = (
            100
            - max(0, commitment - parent.disposable_budget_eur) * 0.8
            - parent.price_sensitivity * 20
            - subscription - subscription_penalty
        )
        noise = rng.uniform(-3, 3)
        metrics = {
            "problem_relevance": self._clamp(relevance + noise),
            "product_clarity": self._clamp(clarity + noise),
            "operational_friction": self._clamp(friction),
            "child_value": self._clamp(child_value + noise),
            "parent_value": self._clamp((relevance + child_value) / 2 + noise),
            "trust": self._clamp(trust + noise),
            "price_fit": self._clamp(price_fit + noise),
            "purchase_interest": self._clamp(
                (relevance + child_value + trust + price_fit) / 4 - 5
                - friction * 0.25 + (clarity - 60) * 0.1
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
            rationale="deterministic zero-cost simulation; not real demand; ASSUMPTION: "
                + "; ".join(assumptions or ["uncalibrated persona/feature scoring"]),
        )
