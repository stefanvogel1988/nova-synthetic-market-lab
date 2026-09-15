"""Independent, zero-cost rubric judgment of synthetic observations."""

from nova_lab.models.experiment import ExperimentObservation
from nova_lab.scoring.bias import apply_positivity_penalty
from nova_lab.scoring.rubrics import parent_product_score, validate_parent_metrics


class RubricJudge:
    def score(self, observation: ExperimentObservation) -> dict[str, float]:
        """Apply the published rubric and objection penalties, not demand proof."""
        return {
            "parent_product_score": apply_positivity_penalty(
                parent_product_score(observation.metrics), observation.objections
            )
        }


def reconcile_parent_product_score(observation: ExperimentObservation) -> float:
    """Validate persisted inputs, preserving a valid replaceable judge's score.

    Legacy rows without a score use the local rubric. An existing score is not
    silently replaced: the JudgeEngine contract allows independent judgments.
    """
    validate_parent_metrics(observation.metrics)
    if "parent_product_score" in observation.metrics:
        return observation.metrics["parent_product_score"]
    return RubricJudge().score(observation)["parent_product_score"]
