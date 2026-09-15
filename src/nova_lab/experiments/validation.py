"""Validate persisted observation coverage against the V1 experiment contracts."""

from nova_lab.experiments.education import SCENARIOS
from nova_lab.experiments.learning import LEARNING_OPTIONS
from nova_lab.experiments.positioning import FRAMINGS
from nova_lab.experiments.pricing import pricing_choices, pricing_contexts, pricing_option
from nova_lab.experiments.privacy import PRIVACY_OPTIONS
from nova_lab.experiments.registry import validate_registry
from nova_lab.experiments.usage import CHECKPOINTS
from nova_lab.models.experiment import ExperimentDefinition, ExperimentObservation
from nova_lab.models.persona import ChildPersona, EducationPersona, ParentPersona
from nova_lab.models.product import ProductVariant


def validate_observations(
    observations: list[ExperimentObservation],
    *,
    run_id: str,
    experiments: list[ExperimentDefinition],
    variants: dict[str, ProductVariant],
    parents: list[ParentPersona],
    children: list[ChildPersona],
    education: list[EducationPersona],
) -> None:
    """Require exactly one observation for every declared trial.

    A trial key is (run, experiment, persona, variant, option). Pricing keys use
    the offered price/subscription, not the resulting choice; other families use
    the selected framing/design/checkpoint/scenario. Choices are validated
    separately so two answers to one pricing offer remain a duplicate trial.
    """
    validate_registry(variants, experiments)
    by_experiment = {experiment.experiment_id: experiment for experiment in experiments}
    by_parent = {parent.persona_id: parent for parent in parents}
    parent_ids = set(by_parent)
    populations = {
        "positioning": parent_ids,
        "pricing": parent_ids,
        "privacy": parent_ids,
        "learning": parent_ids,
        "usage": {child.persona_id for child in children},
        "education": {persona.persona_id for persona in education},
    }
    options = {
        "positioning": set(FRAMINGS),
        "pricing": {pricing_option(context) for context in pricing_contexts()},
        "privacy": set(PRIVACY_OPTIONS),
        "learning": set(LEARNING_OPTIONS),
        "usage": set(CHECKPOINTS),
        "education": set(SCENARIOS),
    }
    expected = {
        (run_id, experiment.experiment_id, persona_id, variant_id, option)
        for experiment in experiments
        for persona_id in populations[experiment.family]
        for variant_id in experiment.variant_ids
        for option in options[experiment.family]
    }
    seen = set()
    for row in observations:
        context = (
            f"run {run_id}, experiment {row.experiment_id}, "
            f"persona {row.persona_id}, variant {row.variant_id}"
        )
        if row.run_id != run_id:
            raise ValueError(f"{context}: mixed run identifiers ({row.run_id})")
        if row.experiment_id not in by_experiment:
            raise ValueError(f"{context}: unknown experiment")
        experiment = by_experiment[row.experiment_id]
        if row.persona_id not in populations[experiment.family]:
            raise ValueError(f"{context}: unexpected persona for {experiment.family}")
        if row.variant_id not in experiment.variant_ids:
            raise ValueError(f"{context}: invalid experiment variant")
        if experiment.family == "pricing":
            option = row.offered_option
            if row.selected_option not in pricing_choices(by_parent[row.persona_id]):
                raise ValueError(f"{context}: invalid pricing choice {row.selected_option!r}")
        else:
            option = row.selected_option
            if row.offered_option is not None:
                raise ValueError(f"{context}: unexpected offered option {row.offered_option!r}")
        if option not in options[experiment.family]:
            raise ValueError(f"{context}: invalid {experiment.family} option {option!r}")
        key = (row.run_id, row.experiment_id, row.persona_id, row.variant_id, option)
        if key in seen:
            raise ValueError(f"{context}: duplicate observation for option {option!r}")
        seen.add(key)
    missing = expected - seen
    if missing:
        raise ValueError(f"missing {len(missing)} expected observations; first key: {min(missing)!r}")
