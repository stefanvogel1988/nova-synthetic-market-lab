from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant
from nova_lab.providers.deterministic import DeterministicEngine
from nova_lab.personas.factory import PersonaFactory
from nova_lab.experiments.registry import load_variants
from pathlib import Path

from nova_lab.scoring.rubrics import PARENT_WEIGHTS


def test_new_components_respond_to_product_inputs_and_seed():
    parent = PersonaFactory(7).make_parents(1)[0]
    variants = load_variants(Path("config/variants.yaml"))
    engine = DeterministicEngine(7)
    basic = engine.evaluate_parent(parent, variants["A"], {})
    curiosity = engine.evaluate_parent(parent, variants["C"], {})
    other_seed = DeterministicEngine(42).evaluate_parent(parent, variants["C"], {})
    for component in ("differentiation", "repeat_use"):
        assert curiosity.metrics[component] > basic.metrics[component]
        assert curiosity.metrics[component] != other_seed.metrics[component]


def test_all_parent_rubric_components_are_explicit_bounded_and_repeatable():
    variants = load_variants(Path("config/variants.yaml"))
    for seed in (1, 7, 42):
        for parent in PersonaFactory(seed).make_parents(10):
            for variant in variants.values():
                context = {"price_eur": 229, "learning_design": "exploration"}
                row = DeterministicEngine(seed).evaluate_parent(parent, variant, context)
                assert PARENT_WEIGHTS.keys() <= row.metrics.keys()
                assert all(0 <= row.metrics[key] <= 100 for key in PARENT_WEIGHTS)
                assert "differentiation" in row.rationale
                assert "repeat_use" in row.rationale
                assert row == DeterministicEngine(seed).evaluate_parent(parent, variant, context)


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


def test_opposed_high_privacy_parent_objects_and_same_seed_repeats_exactly():
    parent = PersonaFactory(7).make_parents(1)[0].model_copy(update={
        "ai_attitude": "opposed", "privacy_concern": 1, "disposable_budget_eur": 75,
    })
    variant = load_variants(Path("config/variants.yaml"))["C"]
    context = {"price_eur": 229, "privacy_mode": "always_on"}
    first = DeterministicEngine(7).evaluate_parent(parent, variant, context)
    assert set(first.objections) >= {"privacy_or_ai_trust", "price"}
    assert first.metrics["trust"] < 10
    assert first == DeterministicEngine(7).evaluate_parent(parent, variant, context)


def test_paired_metrics_do_not_depend_on_labels_or_context_metadata():
    parent = PersonaFactory(7).make_parents(1)[0]
    variant = load_variants(Path("config/variants.yaml"))["C"]
    engine = DeterministicEngine(7)
    first = engine.evaluate_parent(parent, variant, {"run_id": "one", "positioning": "screen-free audio and knowledge box"})
    second = engine.evaluate_parent(parent, variant.model_copy(update={"variant_id": "secret", "label": "Favorite"}),
        {"positioning": "screen-free audio and knowledge box", "run_id": "two"})
    assert first.metrics == second.metrics
