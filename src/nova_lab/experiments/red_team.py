"""Structured findings from a synthetic red-team evaluation."""

from pydantic import BaseModel, Field


class RedTeamFinding(BaseModel):
    """A synthetic critique, including rejection rationale and counterevidence."""

    persona_id: str
    strongest_win: str
    strongest_failure: str
    rejection_issue: str
    score: float = Field(ge=0, le=100)
    evidence_to_change_mind: str
