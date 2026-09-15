from pydantic import BaseModel, model_validator

from nova_lab.models.common import EvidenceStatus


class EvidenceClaim(BaseModel):
    claim_id: str
    claim_text: str
    category: str
    current_status: EvidenceStatus
    supporting_evidence: list[str]
    counterevidence: list[str]
    synthetic_experiments: list[str]
    segment_notes: list[str]
    confidence_note: str
    required_real_world_test: str
    next_decision: str

    @model_validator(mode="after")
    def prohibit_synthetic_only_proven(self):
        if (
            self.current_status == EvidenceStatus.PROVEN
            and self.synthetic_experiments
            and not self.supporting_evidence
        ):
            raise ValueError("synthetic evidence alone cannot establish PROVEN")
        return self
