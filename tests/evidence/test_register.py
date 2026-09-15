from nova_lab.evidence.decision import decide
from nova_lab.evidence.register import EvidenceRegister
from nova_lab.models.common import Decision, EvidenceSourceType, EvidenceStatus
from nova_lab.models.experiment import ExperimentObservation


def test_repeated_synthetic_support_stops_at_supported():
    register = EvidenceRegister()
    register.add_claim("price", "Parents will pay EUR 179", "commercial")

    for experiment_id in ["pricing-1", "pricing-2", "pricing-3"]:
        claim = register.record_synthetic_support(
            "price", experiment_id, "positive synthetic signal"
        )

    assert claim.current_status is EvidenceStatus.SUPPORTED
    assert [evidence.source_type for evidence in claim.supporting_evidence] == [
        EvidenceSourceType.SYNTHETIC_EXPERIMENT,
        EvidenceSourceType.SYNTHETIC_EXPERIMENT,
        EvidenceSourceType.SYNTHETIC_EXPERIMENT,
    ]
    assert decide(claim) is Decision.VALIDATE_WITH_HUMANS


def test_update_from_experiment_records_typed_synthetic_evidence():
    register = EvidenceRegister()
    register.add_claim("price", "Parents will pay EUR 179", "commercial")

    claim = register.update_from_experiment(
        "price",
        [
            ExperimentObservation(
                run_id="run-1",
                experiment_id="pricing-1",
                persona_id="parent-1",
                variant_id="base",
                metrics={"willingness_to_pay": 0.8},
                rationale="The price feels reasonable.",
            )
        ],
    )

    assert claim.current_status is EvidenceStatus.SUPPORTED
    assert len(claim.supporting_evidence) == 1
    source = claim.supporting_evidence[0]
    assert source.source_type is EvidenceSourceType.SYNTHETIC_EXPERIMENT
    assert source.source_id == "pricing-1"
    assert source.description == "The price feels reasonable."


def test_contestation_preserves_counterevidence_and_requires_human_decision():
    register = EvidenceRegister()
    register.add_claim("price", "Parents will pay EUR 179", "commercial")

    claim = register.record_contestation("price", "Budget-sensitive parents objected.")

    assert claim.current_status is EvidenceStatus.CONTESTED
    assert claim.counterevidence == ["Budget-sensitive parents objected."]
    assert decide(claim) is Decision.MODIFY
