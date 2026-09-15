from collections.abc import Iterable

from nova_lab.models.common import EvidenceSourceType, EvidenceStatus
from nova_lab.models.evidence import EvidenceClaim, EvidenceSource
from nova_lab.models.experiment import ExperimentObservation


HUMAN_VALIDATION_ACTIONS = {
    "positioning": "Conduct parent concept interviews",
    "pricing": "Run a parent price smoke test",
    "privacy": "Run moderated parent trust interviews",
    "learning": "Observe parent-child learning sessions",
    "usage": "Run a child-use diary study",
    "education": "Conduct educator classroom-fit interviews",
}


def human_validation_step(category: str, claim_text: str) -> str:
    action = HUMAN_VALIDATION_ACTIONS.get(
        category, "Conduct a claim-specific human interview"
    )
    return f"{action} for: {claim_text}"


class EvidenceRegister:
    def __init__(self):
        self._claims: dict[str, EvidenceClaim] = {}

    def add_claim(self, claim_id: str, text: str, category: str) -> EvidenceClaim:
        claim = EvidenceClaim(
            claim_id=claim_id,
            claim_text=text,
            category=category,
            current_status=EvidenceStatus.ASSUMPTION,
            supporting_evidence=[],
            counterevidence=[],
            synthetic_experiments=[],
            segment_notes=[],
            confidence_note="not yet tested",
            required_real_world_test=human_validation_step(category, text),
            next_decision="VALIDATE_WITH_HUMANS",
        )
        self._claims[claim_id] = claim
        return claim

    def record_synthetic_support(
        self, claim_id: str, experiment_id: str, note: str
    ) -> EvidenceClaim:
        claim = self._claims[claim_id]
        status = (
            EvidenceStatus.CONTESTED
            if claim.current_status is EvidenceStatus.CONTESTED
            else EvidenceStatus.SUPPORTED
        )
        updated = claim.model_copy(
            update={
                "current_status": status,
                "supporting_evidence": [
                    *claim.supporting_evidence,
                    EvidenceSource(
                        source_type=EvidenceSourceType.SYNTHETIC_EXPERIMENT,
                        source_id=experiment_id,
                        description=note,
                    ),
                ],
                "synthetic_experiments": [*claim.synthetic_experiments, experiment_id],
                "confidence_note": note,
                "next_decision": "VALIDATE_WITH_HUMANS",
            }
        )
        self._claims[claim_id] = updated
        return updated

    def update_from_experiment(
        self, claim_id: str, observations: Iterable[ExperimentObservation]
    ) -> EvidenceClaim:
        claim = self._claims[claim_id]
        for observation in observations:
            claim = self.record_synthetic_support(
                claim_id,
                observation.experiment_id,
                observation.rationale or f"Synthetic observation from {observation.run_id}",
            )
            for objection in observation.objections:
                claim = self.record_contestation(claim_id, objection)
        return claim

    def record_contestation(self, claim_id: str, note: str) -> EvidenceClaim:
        claim = self._claims[claim_id]
        updated = claim.model_copy(
            update={
                "current_status": EvidenceStatus.CONTESTED,
                "counterevidence": [*claim.counterevidence, note],
                "next_decision": "VALIDATE_WITH_HUMANS",
            }
        )
        self._claims[claim_id] = updated
        return updated

    def all(self) -> list[EvidenceClaim]:
        return list(self._claims.values())
