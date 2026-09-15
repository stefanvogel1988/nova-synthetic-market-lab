from typing import Protocol

from nova_lab.models.experiment import ExperimentObservation
from nova_lab.models.persona import ParentPersona
from nova_lab.models.product import ProductVariant


class SimulationEngine(Protocol):
    def evaluate_parent(
        self, parent: ParentPersona, variant: ProductVariant, context: dict
    ) -> ExperimentObservation: ...


class JudgeEngine(Protocol):
    def score(self, observation: ExperimentObservation) -> dict[str, float]: ...
