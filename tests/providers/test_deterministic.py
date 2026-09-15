from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant
from nova_lab.providers.deterministic import DeterministicEngine


def test_privacy_first_variant_scores_higher_for_high_privacy_parent():
    parent = ParentPersona(
        persona_id="p",
        child_age=6,
        child_count=1,
        disposable_budget_eur=250,
        price_sensitivity=0.5,
        ai_attitude="cautious",
        privacy_concern=0.95,
        subscription_tolerance=0.3,
        existing_devices=["toniebox"],
        streaming_service="spotify",
        technical_confidence=0.5,
        education_orientation=0.8,
        convenience_orientation=0.7,
        screen_time_philosophy="limited",
        locale_type="suburban",
    )
    normal = ProductVariant(
        variant_id="C",
        label="Curiosity",
        description="x",
        audio_first=True,
        ai_q_and_a=True,
        curiosity_mode=True,
        learning_first=False,
        privacy_first=False,
        education_story=False,
    )
    private = normal.model_copy(update={"variant_id": "E", "privacy_first": True})
    engine = DeterministicEngine(seed=1)

    normal_obs = engine.evaluate_parent(parent, normal, {"price_eur": 179})
    private_obs = engine.evaluate_parent(parent, private, {"price_eur": 179})

    assert private_obs.metrics["trust"] > normal_obs.metrics["trust"]
