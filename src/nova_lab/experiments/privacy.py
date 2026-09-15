"""Synthetic microphone and privacy-design experiments."""

from nova_lab.experiments.runner import ExperimentRunner
from nova_lab.models.experiment import ExperimentDefinition, ExperimentObservation
from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant

PRIVACY_OPTIONS = ["always_on", "push_to_talk", "push_to_talk_kill_switch"]


def privacy_contexts() -> list[dict[str, str]]:
    return [{"privacy_mode": option} for option in PRIVACY_OPTIONS]


def run_privacy(
    runner: ExperimentRunner,
    run_id: str,
    experiment: ExperimentDefinition,
    parents: list[ParentPersona],
    variants: dict[str, ProductVariant],
) -> list[ExperimentObservation]:
    """Evaluate each microphone/privacy option once per parent/variant pairing."""
    observations: list[ExperimentObservation] = []
    for context in privacy_contexts():
        option = context["privacy_mode"]
        for observation in runner.run_parent_experiment(
            run_id, experiment, parents, variants, context
        ):
            observations.append(
                observation.model_copy(
                    update={
                        "selected_option": option,
                        "rationale": (
                            f"{observation.rationale}; synthetic-only privacy result; "
                            "not evidence of real-world trust"
                        ),
                    }
                )
            )
    return observations
