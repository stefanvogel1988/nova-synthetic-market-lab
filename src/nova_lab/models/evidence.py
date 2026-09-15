from pydantic import BaseModel, model_validator

from nova_lab.models.common import EvidenceSourceType, EvidenceStatus


class EvidenceSource(BaseModel):
    source_type: EvidenceSourceType
    source_id: str
    description: str


class EvidenceClaim(BaseModel):
    claim_id: str
    claim_text: str
    category: str
    current_status: EvidenceStatus
    supporting_evidence: list[EvidenceSource]
    counterevidence: list[str]
    synthetic_experiments: list[str]
    segment_notes: list[str]
    confidence_note: str
    required_real_world_test: str
    next_decision: str

    @model_validator(mode="after")
    def require_provenance_for_proven(self):
        if self.current_status == EvidenceStatus.PROVEN and not any(
            evidence.source_type
            in {
                EvidenceSourceType.EXTERNAL_RELIABLE,
                EvidenceSourceType.DIRECT_HUMAN_OBSERVATION,
            }
            for evidence in self.supporting_evidence
        ):
            raise ValueError(
                "PROVEN requires reliable external evidence or direct human observation"
            )
        return self
