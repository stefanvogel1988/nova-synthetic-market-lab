"""Synthetic positioning-framing experiments."""

from nova_lab.experiments.runner import ExperimentRunner
from nova_lab.models.experiment import ExperimentDefinition, ExperimentObservation
from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant

FRAMINGS = [
    "AI music box for children",
    "screen-free audio and knowledge box",
    "music, stories and knowledge without a screen",
    "screen-free curiosity companion",
]


def positioning_contexts() -> list[dict[str, str]]:
    return [{"positioning": framing} for framing in FRAMINGS]


def run_positioning(
    runner: ExperimentRunner,
    run_id: str,
    experiment: ExperimentDefinition,
    parents: list[ParentPersona],
    variants: dict[str, ProductVariant],
) -> list[ExperimentObservation]:
    """Evaluate each framing once for every parent/variant pairing."""
    observations: list[ExperimentObservation] = []
    for context in positioning_contexts():
        framing = context["positioning"]
        for observation in runner.run_parent_experiment(
            run_id, experiment, parents, variants, context
        ):
            observations.append(
                observation.model_copy(
                    update={
                        "selected_option": framing,
                        "rationale": (
                            f"{observation.rationale}; synthetic-only positioning result; "
                            "not real purchase intent"
                        ),
                    }
                )
            )
    return observations
