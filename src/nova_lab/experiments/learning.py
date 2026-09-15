"""Synthetic learning-interaction design experiments."""

from nova_lab.experiments.runner import ExperimentRunner
from nova_lab.models.experiment import ExperimentDefinition, ExperimentObservation
from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant

LEARNING_OPTIONS = ["direct", "follow_up", "exploration"]


def learning_contexts() -> list[dict[str, str]]:
    return [{"learning_design": option} for option in LEARNING_OPTIONS]


def run_learning(
    runner: ExperimentRunner,
    run_id: str,
    experiment: ExperimentDefinition,
    parents: list[ParentPersona],
    variants: dict[str, ProductVariant],
) -> list[ExperimentObservation]:
    """Evaluate each learning design once per parent/variant pairing."""
    observations: list[ExperimentObservation] = []
    for context in learning_contexts():
        option = context["learning_design"]
        for observation in runner.run_parent_experiment(
            run_id, experiment, parents, variants, context
        ):
            observations.append(
                observation.model_copy(
                    update={
                        "selected_option": option,
                        "rationale": (
                            f"{observation.rationale}; synthetic-only learning-design result; "
                            "not evidence of learning outcomes"
                        ),
                    }
                )
            )
    return observations
