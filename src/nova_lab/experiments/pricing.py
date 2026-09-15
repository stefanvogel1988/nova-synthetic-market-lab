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
    three_month_commitment = device_price + monthly_subscription * 3
    return three_month_commitment <= gift_budget


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
    by_parent = {parent.persona_id: parent for parent in parents}
    for context in pricing_contexts():
        option = f"{context['price_eur']}/{context['subscription_eur']}"
        for observation in runner.run_parent_experiment(
            run_id, experiment, parents, variants, context
        ):
            parent = by_parent[observation.persona_id]
            price, subscription = context["price_eur"], context["subscription_eur"]
            # Explicit uncalibrated proxy for competing family spending. Existing
            # audio hardware increases the opportunity cost of another device.
            competing_budget = parent.disposable_budget_eur * (0.25 if parent.existing_devices else 0.10)
            available = parent.disposable_budget_eur - competing_budget
            fits = affordable(price, subscription, available)
            tolerates = subscription <= 9.99 * parent.subscription_tolerance
            selected = fits and tolerates and observation.metrics["purchase_interest"] >= 50
            objections = list(observation.objections)
            if not fits:
                objections.append("price")
            if not tolerates:
                objections.append("subscription")
            if not selected:
                objections.append("would_not_buy")
            decision = "buy_nova" if selected else "competing_purchase" if parent.existing_devices else "defer"
            observations.append(
                observation.model_copy(
                    update={
                        "offered_option": option,
                        "selected_option": decision,
                        "objections": sorted(set(objections)),
                        "metrics": {**observation.metrics,
                            "commitment_eur": round(price + 3 * subscription, 2),
                            "available_budget_eur": round(available, 2),
                            "competing_budget_eur": round(competing_budget, 2),
                            "selected_nova": float(selected)},
                        "rationale": (
                            f"{observation.rationale}; synthetic-only pricing result; "
                            "not real demand or willingness to pay; ASSUMPTION: three-month commitment; "
                            "reserve 25% of budget for competing purchases when devices are owned, otherwise 10%; "
                            "monthly tolerance ceiling=9.99*tolerance; select only if affordable, tolerated and interest>=50"
                        ),
                    }
                )
            )
    return observations
