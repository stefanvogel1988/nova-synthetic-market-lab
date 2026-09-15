"""Structured findings from a synthetic red-team evaluation."""

from pydantic import BaseModel, Field
import random

from nova_lab.models.persona import RedTeamPersona


class RedTeamFinding(BaseModel):
    """A synthetic critique, including rejection rationale and counterevidence."""

    persona_id: str
    strongest_win: str
    strongest_failure: str
    rejection_issue: str
    score: float = Field(ge=0, le=100)
    evidence_to_change_mind: str


# These are disclosed synthetic proxies, not evidence of investment or safety.
ROLE_FOCUS = {
    "consumer_vc": ("purchase_interest", "observed purchase decisions"),
    "hardware_vc": ("price_fit", "hardware cost and reliability trials"),
    "cfo": ("price_fit", "verified unit economics and willingness to pay"),
    "child_development": ("child_value", "observed age-appropriate child trials"),
    "elementary_education": ("child_value", "teacher-led learning evaluations"),
    "media_safety": ("trust", "classified real product safety responses"),
    "privacy_lawyer": ("trust", "documented data flows and legal review"),
    "cybersecurity": ("trust", "independent security testing"),
    "audio_product": ("parent_value", "audio usability and reliability trials"),
    "competitive_strategy": ("problem_relevance", "real comparative product trials"),
    "skeptical_parent": ("purchase_interest", "family trials and purchase decisions"),
    "school_procurement": ("price_fit", "institutional procurement and deployment trials"),
}


def assess_independently(
    members: list[RedTeamPersona], metrics: dict[str, float], seed: int
) -> dict[str, RedTeamFinding]:
    """Judge each role's own proxy before exposing any peer judgments."""
    findings = {}
    for member in members:
        metric, required_evidence = ROLE_FOCUS[member.role]
        rng = random.Random(f"red-team:{seed}:{member.persona_id}:{member.role}")
        score = round(max(0, min(100,
            metrics[metric] - member.rejection_bias * 15 + rng.uniform(-3, 3)
        )), 2)
        findings[member.persona_id] = RedTeamFinding(
            persona_id=member.persona_id,
            strongest_win=f"Modeled {metric}={metrics[metric]:.2f}/100 offers a synthetic signal for {member.role}",
            strongest_failure=f"{metric} is only a parent-model proxy; no {required_evidence}",
            rejection_issue=f"{member.role} requires {required_evidence}; current synthetic proxy score={score:.2f}/100",
            score=score,
            evidence_to_change_mind=required_evidence,
        )
    return findings


def peer_critiques(
    member: RedTeamPersona, findings: dict[str, RedTeamFinding]
) -> list[dict]:
    """Translate other roles' evidence-gap critiques into auditable adjustments.

    Severity is the peer's distance below 100, normalized to 0–1. Each member
    applies its own skepticism to the mean peer severity, with a maximum
    12-point reduction. This rule is a deterministic modeling assumption.
    """
    peers = [findings[key] for key in sorted(findings) if key != member.persona_id]
    return [{
        "persona_id": peer.persona_id,
        "rejection_issue": peer.rejection_issue,
        "severity": round((100 - peer.score) / 100, 4),
        "adjustment": -round((100 - peer.score) / 100 * member.rejection_bias * 12 / len(peers), 4),
    } for peer in peers]
