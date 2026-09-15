from nova_lab.personas.factory import PersonaFactory
from nova_lab.personas.validation import validate_parent_population


def test_parent_population_is_deterministic_and_diverse():
    a = PersonaFactory(seed=7).make_parents(150)
    b = PersonaFactory(seed=7).make_parents(150)

    assert a == b
    assert len(a) == 150
    assert len({parent.ai_attitude for parent in a}) >= 4
    assert len({parent.streaming_service for parent in a}) >= 4
    assert any(parent.privacy_concern >= 0.8 for parent in a)
    assert any(parent.ai_attitude == "opposed" for parent in a)
    assert all(parent.disposable_budget_eur >= 0 for parent in a)
    assert validate_parent_population(a) == []


def test_factory_generates_required_non_parent_populations():
    factory = PersonaFactory(seed=11)

    children = factory.make_children(30)
    education = factory.make_education(20)
    red_team = factory.make_red_team()

    assert len(children) == 30
    assert len(education) == 20
    assert len(red_team) == 12
    assert any(person.role == "skeptical_parent" for person in red_team)
    assert any(person.rejection_bias >= 0.8 for person in red_team)
