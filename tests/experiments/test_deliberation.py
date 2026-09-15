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


def test_red_team_initial_judgments_depend_on_role_and_not_panel_order():
    from nova_lab.experiments.red_team import assess_independently
    from nova_lab.personas.factory import PersonaFactory

    members = PersonaFactory(7).make_red_team()
    metrics = {"purchase_interest": 70, "price_fit": 35, "child_value": 80,
               "trust": 25, "parent_value": 65, "problem_relevance": 60}
    first = assess_independently(members, metrics, seed=7)
    reordered = assess_independently(list(reversed(members)), metrics, seed=7)

    assert first == reordered
    assert len({finding.score for finding in first.values()}) > 1
    stronger_trust = assess_independently(members, {**metrics, "trust": 90}, seed=7)
    assert stronger_trust["red-06"].score > first["red-06"].score
    assert stronger_trust["red-02"].score == first["red-02"].score


def test_peer_critique_changes_post_scores_without_rewriting_initial_judgments():
    from nova_lab.experiments.red_team import assess_independently, peer_critiques
    from nova_lab.personas.factory import PersonaFactory

    members = PersonaFactory(7).make_red_team()
    metrics = {"purchase_interest": 70, "price_fit": 35, "child_value": 80,
               "trust": 25, "parent_value": 65, "problem_relevance": 60}
    findings = assess_independently(members, metrics, seed=7)
    pre_scores = {key: finding.score for key, finding in findings.items()}
    softened = {**findings, "red-06": findings["red-06"].model_copy(update={"score": 95})}

    def evaluate(critique_findings):
        adjustments = {
            member.persona_id: sum(item["adjustment"] for item in peer_critiques(member, critique_findings))
            for member in members
        }
        return deliberate(pre_scores, adjustments)

    original = evaluate(findings)
    revised = evaluate(softened)
    assert original.pre_scores == revised.pre_scores == pre_scores
    assert revised.post_scores["red-00"] > original.post_scores["red-00"]
    assert revised.post_scores["red-06"] == original.post_scores["red-06"]
    assert len(set(revised.post_scores.values())) > 1
