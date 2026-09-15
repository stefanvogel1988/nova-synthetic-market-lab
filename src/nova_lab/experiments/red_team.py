"""Structured findings from a synthetic red-team evaluation."""

from pydantic import BaseModel, Field
import random
from typing import Annotated

from nova_lab.experiments.investment_committee import InvestmentCommitteeResult, deliberate
from nova_lab.models.persona import RedTeamPersona


RedTeamScore = Annotated[float, Field(ge=0, le=100)]


class RedTeamFinding(BaseModel):
    """A synthetic critique, including rejection rationale and counterevidence."""

    persona_id: str
    strongest_win: str
    strongest_failure: str
    rejection_issue: str
    score: RedTeamScore
    evidence_to_change_mind: str


class RedTeamRecord(RedTeamPersona):
    """The complete persisted member judgment and peer-deliberation snapshot."""

    run_id: str
    pre_score: RedTeamScore
    post_score: RedTeamScore
    finding: RedTeamFinding
    peer_critiques: list[dict]


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


def validate_red_team_records(
    rows: list[dict], *, run_id: str, members: list[RedTeamPersona], committee: dict,
) -> None:
    """Reconcile persisted records using the existing panel and deliberation rules.

    V1 findings are embedded in their member record and keyed by persona_id;
    there is no separate finding ID or contradiction-state field.
    """
    expected_members = {member.persona_id: member for member in members}
    records = {}
    for row in rows:
        record = RedTeamRecord.model_validate(row)
        key = record.persona_id
        context = f"run {run_id}, red-team persona {key}"
        if record.run_id != run_id:
            raise ValueError(f"{context}: mixed run identifiers")
        if key not in expected_members:
            raise ValueError(f"{context}: unexpected persona")
        if key in records:
            raise ValueError(f"{context}: duplicate record")
        if RedTeamPersona.model_validate(row) != expected_members[key]:
            raise ValueError(f"{context}: persona differs from the run's panel")
        if record.finding.persona_id != key:
            raise ValueError(f"{context}: finding persona does not match record")
        if record.pre_score != record.finding.score:
            raise ValueError(f"{context}: pre_score differs from finding.score")
        records[key] = record
    if records.keys() != expected_members.keys():
        raise ValueError(f"run {run_id}: missing expected red-team records")

    findings = {key: record.finding for key, record in records.items()}
    adjustments = {}
    for key, record in records.items():
        expected_peers = peer_critiques(expected_members[key], findings)
        if record.peer_critiques != expected_peers:
            raise ValueError(f"run {run_id}, red-team persona {key}: inconsistent peer_critiques")
        adjustments[key] = sum(peer["adjustment"] for peer in expected_peers)
    expected_committee = deliberate(
        {key: record.pre_score for key, record in records.items()}, adjustments,
    )
    for key, record in records.items():
        if record.post_score != expected_committee.post_scores[key]:
            raise ValueError(f"run {run_id}, red-team persona {key}: inconsistent post_score")
    if InvestmentCommitteeResult.model_validate(committee) != expected_committee:
        raise ValueError(f"run {run_id}: inconsistent investment_committee snapshot")
