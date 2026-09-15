import random

from nova_lab.models.experiment import ExperimentDefinition, ExperimentObservation
from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant
from nova_lab.providers.base import SimulationEngine


def blinded_order(items: list[str], seed: int, salt: str) -> list[str]:
    result = list(items)
    random.Random(f"{seed}:{salt}").shuffle(result)
    return result


class ExperimentRunner:
    def __init__(self, engine: SimulationEngine, seed: int):
        self.engine = engine
        self.seed = seed

    def run_parent_experiment(
        self,
        run_id: str,
        experiment: ExperimentDefinition,
        parents: list[ParentPersona],
        variants: dict[str, ProductVariant],
        context: dict | None = None,
    ) -> list[ExperimentObservation]:
        observations: list[ExperimentObservation] = []
        context = dict(context or {})
        for parent in parents:
            for index, variant_id in enumerate(blinded_order(
                experiment.variant_ids, self.seed, parent.persona_id
            ), start=1):
                merged = {
                    **context,
                    "run_id": run_id,
                    "experiment_id": experiment.experiment_id,
                }
                blind_id = f"concept-{index:02d}"
                blinded = variants[variant_id].model_copy(update={
                    "variant_id": blind_id, "label": f"Concept {index:02d}",
                })
                observation = self.engine.evaluate_parent(parent, blinded, merged)
                observations.append(observation.model_copy(update={
                    "variant_id": variant_id, "blinded_variant_id": blind_id,
                }))
        return observations
