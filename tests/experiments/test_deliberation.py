import pytest

from nova_lab.experiments.focus_group import run_focus_group
from nova_lab.experiments.investment_committee import deliberate
from nova_lab.experiments.red_team import RedTeamFinding


def test_focus_group_keeps_initial_and_final_synthetic_positions():
    """A missing critique update would leave the final synthetic scores unchanged."""
    result = run_focus_group(
        initial_positions={"p1": 80, "p2": 25},
        critique_effects={"p1": -10, "p2": 5},
    )

    assert result.initial_scores == {"p1": 80, "p2": 25}
    assert result.final_scores == {"p1": 70, "p2": 30}
    assert len(set(result.final_scores.values())) > 1


def test_red_team_finding_requires_rejection_counterevidence_and_bounded_score():
    """Removing a required red-team field or score validation is a contract bug."""
    finding = RedTeamFinding(
        persona_id="synthetic-red-team-1",
        strongest_win="Clear offline play value.",
        strongest_failure="The recurring cost is difficult to justify.",
        rejection_issue="No convincing explanation of long-term value.",
        score=35,
        evidence_to_change_mind="A controlled synthetic retention result.",
    )

    assert finding.rejection_issue == "No convincing explanation of long-term value."
    assert finding.evidence_to_change_mind == "A controlled synthetic retention result."
    with pytest.raises(ValueError):
        RedTeamFinding(
            persona_id="synthetic-red-team-1",
            strongest_win="Clear offline play value.",
            strongest_failure="The recurring cost is difficult to justify.",
            rejection_issue="No convincing explanation of long-term value.",
            score=101,
            evidence_to_change_mind="A controlled synthetic retention result.",
        )


def test_investment_committee_preserves_pre_and_post_peer_critique_scores():
    """Ignoring peer critique would make the post-deliberation result incorrect."""
    result = deliberate(
        pre_scores={"synthetic-member-a": 80, "synthetic-member-b": 15},
        peer_adjustments={"synthetic-member-a": -15, "synthetic-member-b": 20},
    )

    assert result.pre_scores == {"synthetic-member-a": 80, "synthetic-member-b": 15}
    assert result.post_scores == {"synthetic-member-a": 65, "synthetic-member-b": 35}
