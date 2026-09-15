import pytest
from pydantic import ValidationError

from nova_lab.models.common import EvidenceSourceType, EvidenceStatus
from nova_lab.models.evidence import EvidenceClaim, EvidenceSource
from nova_lab.models.persona import ParentPersona


def test_parent_budget_must_be_non_negative():
    with pytest.raises(ValidationError):
        ParentPersona(
            persona_id="p1",
            child_age=6,
            child_count=1,
            disposable_budget_eur=-1,
            price_sensitivity=0.5,
            ai_attitude="cautious",
            privacy_concern=0.8,
            subscription_tolerance=0.2,
            existing_devices=[],
            streaming_service="spotify",
            technical_confidence=0.5,
            education_orientation=0.7,
            convenience_orientation=0.6,
            screen_time_philosophy="limited",
            locale_type="suburban",
        )


def test_synthetic_claim_cannot_be_marked_proven_without_external_evidence():
    with pytest.raises(ValidationError):
        EvidenceClaim(
            claim_id="c1",
            claim_text="Parents will pay 179 EUR",
            category="commercial",
            current_status=EvidenceStatus.PROVEN,
            supporting_evidence=[],
            counterevidence=[],
            synthetic_experiments=["pricing-v1"],
            segment_notes=[],
            confidence_note="synthetic only",
            required_real_world_test="preorder",
            next_decision="VALIDATE_WITH_HUMANS",
        )


def test_synthetic_supporting_source_cannot_bypass_proven_guard():
    with pytest.raises(ValidationError):
        EvidenceClaim(
            claim_id="c2",
            claim_text="Parents will pay 179 EUR",
            category="commercial",
            current_status=EvidenceStatus.PROVEN,
            supporting_evidence=[
                EvidenceSource(
                    source_type=EvidenceSourceType.SYNTHETIC_EXPERIMENT,
                    source_id="pricing-v1",
                    description="Synthetic pricing simulation",
                )
            ],
            counterevidence=[],
            synthetic_experiments=["pricing-v1"],
            segment_notes=[],
            confidence_note="synthetic only",
            required_real_world_test="preorder",
            next_decision="VALIDATE_WITH_HUMANS",
        )


def test_reliable_external_source_can_support_proven_claim():
    claim = EvidenceClaim(
        claim_id="c3",
        claim_text="Parents will pay 179 EUR",
        category="commercial",
        current_status=EvidenceStatus.PROVEN,
        supporting_evidence=[
            EvidenceSource(
                source_type=EvidenceSourceType.EXTERNAL_RELIABLE,
                source_id="market-study-2026",
                description="Published market study",
            )
        ],
        counterevidence=[],
        synthetic_experiments=["pricing-v1"],
        segment_notes=[],
        confidence_note="supported by external research",
        required_real_world_test="preorder",
        next_decision="VALIDATE_WITH_HUMANS",
    )

    assert claim.current_status is EvidenceStatus.PROVEN
