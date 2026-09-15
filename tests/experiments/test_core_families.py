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
        assert [item.offered_option if run_family is run_pricing else item.selected_option for item in matching] == expected_options
    assert all(item.run_id == "core-family-run" for item in observations)
    assert all(item.experiment_id == "core-family-test" for item in observations)
    assert all(item.metrics for item in observations)
    assert all("synthetic-only" in item.rationale for item in observations)


def test_pricing_decisions_enforce_commitment_subscription_and_competing_spend(parent, experiment):
    variants = load_variants(Path("config/variants.yaml"))
    willing = parent.model_copy(update={"disposable_budget_eur": 250, "existing_devices": [],
        "price_sensitivity": 0, "ai_attitude": "enthusiastic", "privacy_concern": 0,
        "education_orientation": 1, "subscription_tolerance": 1})

    def offers(persona):
        rows = run_pricing(ExperimentRunner(DeterministicEngine(3), 8), "r", experiment, [persona], variants)
        return {row.offered_option: row for row in rows if row.variant_id == "E"}

    accepted = offers(willing)
    assert accepted["179/0"].selected_option == "buy_nova"
    assert accepted["229/9.99"].selected_option != "buy_nova"
    assert "price" in accepted["229/9.99"].objections
    assert accepted["179/9.99"].metrics["purchase_interest"] < accepted["179/0"].metrics["purchase_interest"]
    assert offers(willing.model_copy(update={"subscription_tolerance": 0}))["179/4.99"].selected_option != "buy_nova"
    assert accepted["199/0"].selected_option == "buy_nova"
    assert offers(willing.model_copy(update={"existing_devices": ["toniebox"]}))["199/0"].selected_option == "competing_purchase"
    assert all(row.selected_option != "buy_nova" for row in offers(willing.model_copy(update={"disposable_budget_eur": 75})).values())


@pytest.mark.parametrize(("family", "option_key", "first", "second", "metric"), [
    (run_positioning, "positioning", FRAMINGS[0], FRAMINGS[1], "product_clarity"),
    (run_privacy, "privacy_mode", "always_on", "push_to_talk_kill_switch", "trust"),
    (run_learning, "learning_design", "direct", "exploration", "child_value"),
])
def test_options_change_declared_metrics_with_disclosed_assumptions(parent, experiment, family, option_key, first, second, metric):
    parent = parent.model_copy(update={"privacy_concern": 1, "education_orientation": 1})
    rows = family(ExperimentRunner(DeterministicEngine(3), 8), "r", experiment, [parent], load_variants(Path("config/variants.yaml")))
    paired = {row.selected_option: row for row in rows if row.variant_id == "C"}
    assert metric in paired[first].metrics
    assert paired[second].metrics[metric] - paired[first].metrics[metric] >= 10
    assert paired[second].metrics["purchase_interest"] != paired[first].metrics["purchase_interest"]
    assert all("ASSUMPTION" in row.rationale and option_key in row.rationale for row in paired.values())


def test_learning_exploration_can_be_unfavorable_for_convenience_oriented_parent(parent, experiment):
    parent = parent.model_copy(update={"education_orientation": 0, "convenience_orientation": 1})
    rows = run_learning(ExperimentRunner(DeterministicEngine(3), 8), "r", experiment, [parent], load_variants(Path("config/variants.yaml")))
    paired = {row.selected_option: row for row in rows if row.variant_id == "C"}
    assert paired["exploration"].metrics["purchase_interest"] < paired["direct"].metrics["purchase_interest"]
    assert paired["exploration"].metrics["operational_friction"] > paired["direct"].metrics["operational_friction"]
