from nova_lab.models.common import Decision, EvidenceStatus
from nova_lab.models.evidence import EvidenceClaim


def decide(claim: EvidenceClaim) -> Decision:
    if claim.current_status is EvidenceStatus.CONTESTED:
        return Decision.MODIFY
    if claim.current_status in {
        EvidenceStatus.ASSUMPTION,
        EvidenceStatus.UNKNOWN,
        EvidenceStatus.SUPPORTED,
    }:
        return Decision.VALIDATE_WITH_HUMANS
    return Decision.CONTINUE
