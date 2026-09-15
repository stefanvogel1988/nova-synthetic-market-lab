from pathlib import Path

import pytest

from nova_lab.experiments.learning import LEARNING_OPTIONS, run_learning
from nova_lab.experiments.positioning import FRAMINGS, run_positioning
from nova_lab.experiments.privacy import PRIVACY_OPTIONS, run_privacy
from nova_lab.experiments.pricing import PRICES, SUBSCRIPTIONS, affordable, run_pricing
from nova_lab.experiments.registry import load_variants
from nova_lab.experiments.runner import ExperimentRunner
from nova_lab.models.experiment import ExperimentDefinition
from nova_lab.models.persona import ParentPersona
from nova_lab.providers.deterministic import DeterministicEngine


def test_price_test_enforces_household_budget():
    assert affordable(device_price=179, monthly_subscription=7.99, gift_budget=250) is True
    assert affordable(device_price=229, monthly_subscription=9.99, gift_budget=200) is False


@pytest.fixture
def parent() -> ParentPersona:
    return ParentPersona(
        persona_id="price-conscious-parent",
        child_age=7,
        child_count=1,
        disposable_budget_eur=250,
        price_sensitivity=0.8,
        ai_attitude="pragmatic",
        privacy_concern=0.7,
        subscription_tolerance=0.4,
        existing_devices=["speaker"],
        streaming_service="spotify",
        technical_confidence=0.6,
        education_orientation=0.7,
        convenience_orientation=0.5,
        screen_time_philosophy="limited",
        locale_type="suburban",
    )


@pytest.fixture
def experiment() -> ExperimentDefinition:
    return ExperimentDefinition(
        experiment_id="core-family-test",
        family="core",
        hypothesis="Synthetic options are comparable.",
        success_criteria="Every option is represented.",
        scenario="A controlled synthetic parent evaluation.",
        variant_ids=["C", "E"],
    )


@pytest.mark.parametrize(
    ("run_family", "expected_options"),
    [
        (run_positioning, FRAMINGS),
        (run_privacy, PRIVACY_OPTIONS),
        (run_learning, LEARNING_OPTIONS),
        (run_pricing, [f"{price}/{subscription}" for price in PRICES for subscription in SUBSCRIPTIONS]),
    ],
)
def test_each_family_emits_every_option_once_per_parent_variant_and_is_synthetic_only(
    run_family, expected_options, parent, experiment
):
    observations = run_family(
        runner=ExperimentRunner(DeterministicEngine(seed=3), seed=8),
        run_id="core-family-run",
        experiment=experiment,
        parents=[parent],
        variants=load_variants(Path("config/variants.yaml")),
    )

    assert len(observations) == len(expected_options) * 2
    for variant_id in ("C", "E"):
        matching = [item for item in observations if item.variant_id == variant_id]
        assert [item.selected_option for item in matching] == expected_options
    assert all(item.run_id == "core-family-run" for item in observations)
    assert all(item.experiment_id == "core-family-test" for item in observations)
    assert all(item.metrics for item in observations)
    assert all("synthetic-only" in item.rationale for item in observations)
