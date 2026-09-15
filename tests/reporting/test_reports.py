from pathlib import Path

from nova_lab.evidence.register import EvidenceRegister
from nova_lab.models.common import EvidenceSourceType, EvidenceStatus
from nova_lab.models.evidence import EvidenceClaim, EvidenceSource
from nova_lab.reporting.context import ExecutiveFinding, build_report_context
from nova_lab.reporting.markdown import render_markdown


def test_investor_report_contains_synthetic_disclaimer():
    text = render_markdown(
        Path("templates/investor_summary.md.j2"),
        {"proven": [], "synthetic": [], "contested": [], "human_tests": []},
    )

    assert "does not prove product-market fit" in text.lower()
    assert "PROVEN" in text
    assert "SYNTHETIC" in text


def test_report_context_separates_proven_claims_from_synthetic_findings():
    proven = EvidenceClaim(
        claim_id="observed-trust",
        claim_text="Observed parents prefer a physical microphone switch.",
        category="trust",
        current_status=EvidenceStatus.PROVEN,
        supporting_evidence=[
            EvidenceSource(
                source_type=EvidenceSourceType.DIRECT_HUMAN_OBSERVATION,
                source_id="interview-1",
                description="Parent interview",
            )
        ],
        counterevidence=[],
        synthetic_experiments=[],
        segment_notes=[],
        confidence_note="Observed in interview",
        required_real_world_test="Replicate with additional parents",
        next_decision="CONTINUE",
    )
    supported = EvidenceClaim(
        claim_id="price",
        claim_text="Parents will pay EUR 179.",
        category="commercial",
        current_status=EvidenceStatus.SUPPORTED,
        supporting_evidence=[],
        counterevidence=[],
        synthetic_experiments=["pricing-1"],
        segment_notes=[],
        confidence_note="Synthetic signal only",
        required_real_world_test="Run a parent price smoke test",
        next_decision="VALIDATE_WITH_HUMANS",
    )

    context = build_report_context([proven, supported])

    assert [finding.text for finding in context["proven"]] == [proven.claim_text]
    assert [finding.text for finding in context["synthetic"]] == [supported.claim_text]
    assert proven.claim_text not in [finding.text for finding in context["synthetic"]]
    assert [finding.text for finding in context["human_tests"]] == [
        supported.required_real_world_test
    ]


def test_executive_report_labels_each_section_finding_with_its_evidence_status():
    context = build_report_context(
        product_ranking=[
            ExecutiveFinding(
                status=EvidenceStatus.SUPPORTED,
                text="Privacy-first NOVA ranks highest in the simulation.",
            )
        ]
    )

    text = render_markdown(Path("templates/executive_report.md.j2"), context)

    assert "- [SUPPORTED] Privacy-first NOVA ranks highest in the simulation." in text


def test_executive_report_discloses_rubric_components_weights_and_uncalibrated_assumptions():
    text = render_markdown(
        Path("templates/executive_report.md.j2"), build_report_context()
    )

    assert "## Scoring assumptions and weights" in text
    for component, weight in (
        ("problem_relevance", 15), ("product_clarity", 10), ("child_value", 15),
        ("parent_value", 10), ("trust", 15), ("differentiation", 10),
        ("repeat_use", 10), ("price_fit", 10), ("operational_friction", 5),
    ):
        assert f"{component}: {weight}%" in text
    assert "100 - operational_friction" in text
    assert "8 points" in text
    assert "differentiation and repeat_use are uncalibrated design heuristics" in text
    assert "not observed differentiation or retention" in text
    assert "does not prove product-market fit" in text


def test_executive_report_labels_human_test_fallback_as_unknown():
    supported = EvidenceClaim(
        claim_id="price",
        claim_text="Parents will pay EUR 179.",
        category="commercial",
        current_status=EvidenceStatus.SUPPORTED,
        supporting_evidence=[],
        counterevidence=[],
        synthetic_experiments=["pricing-1"],
        segment_notes=[],
        confidence_note="Synthetic signal only",
        required_real_world_test="Run a parent price smoke test",
        next_decision="VALIDATE_WITH_HUMANS",
    )

    text = render_markdown(
        Path("templates/executive_report.md.j2"), build_report_context([supported])
    )

    assert "- [UNKNOWN] Run a parent price smoke test" in text


def test_human_validation_steps_are_concrete_deduplicated_and_sorted():
    """Retaining generic/repeated human-validation text would hide next actions."""
    register = EvidenceRegister()
    register.add_claim(
        "usage-1",
        "Curiosity Mode retains meaningful self-initiated use after novelty decays.",
        "usage",
    )
    register.add_claim(
        "pricing-1", "Parents will pay EUR 179.", "pricing"
    )
    register.add_claim(
        "pricing-duplicate", "Parents will pay EUR 179.", "pricing"
    )

    context = build_report_context(register.all())

    assert [item.label for item in context["human_tests"]] == [
        "[UNKNOWN] Run a child-use diary study for: Curiosity Mode retains meaningful self-initiated use after novelty decays.",
        "[UNKNOWN] Run a parent price smoke test for: Parents will pay EUR 179.",
    ]
