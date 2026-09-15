"""Independent, zero-cost rubric judgment of synthetic observations."""

from nova_lab.models.experiment import ExperimentObservation
from nova_lab.scoring.bias import apply_positivity_penalty
from nova_lab.scoring.rubrics import parent_product_score


class RubricJudge:
    def score(self, observation: ExperimentObservation) -> dict[str, float]:
        """Apply the published rubric and objection penalties, not demand proof."""
        return {
            "parent_product_score": apply_positivity_penalty(
                parent_product_score(observation.metrics), observation.objections
            )
        }
