"""Constrained synthetic pricing experiment contexts."""

from nova_lab.experiments.runner import ExperimentRunner
from nova_lab.models.experiment import ExperimentDefinition, ExperimentObservation
from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant

PRICES = [149, 179, 199, 229]
SUBSCRIPTIONS = [0, 4.99, 7.99, 9.99]


def affordable(
    device_price: float, monthly_subscription: float, gift_budget: float
) -> bool:
    """Return whether a three-month subscription commitment fits the budget."""
    first_year_commitment = device_price + monthly_subscription * 3
    return first_year_commitment <= gift_budget


def pricing_contexts() -> list[dict[str, float | int]]:
    """Return every declared device/subscription combination exactly once."""
    return [
        {"price_eur": price, "subscription_eur": subscription}
        for price in PRICES
        for subscription in SUBSCRIPTIONS
    ]


def run_pricing(
    runner: ExperimentRunner,
    run_id: str,
    experiment: ExperimentDefinition,
    parents: list[ParentPersona],
    variants: dict[str, ProductVariant],
) -> list[ExperimentObservation]:
    """Evaluate every constrained price/subscription choice locally."""
    observations: list[ExperimentObservation] = []
    for context in pricing_contexts():
        option = f"{context['price_eur']}/{context['subscription_eur']}"
        for observation in runner.run_parent_experiment(
            run_id, experiment, parents, variants, context
        ):
            observations.append(
                observation.model_copy(
                    update={
                        "selected_option": option,
                        "rationale": (
                            f"{observation.rationale}; synthetic-only pricing result; "
                            "not real demand or willingness to pay"
                        ),
                    }
                )
            )
    return observations
