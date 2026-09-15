from nova_lab.personas.factory import PersonaFactory
from nova_lab.personas.validation import validate_parent_population
from nova_lab.personas.validation import validate_population


def test_parent_population_is_reproducible_for_same_seed():
    a = PersonaFactory(seed=7).make_parents(150)
    b = PersonaFactory(seed=7).make_parents(150)

    assert a == b


def test_parent_population_changes_for_a_different_seed():
    first = PersonaFactory(seed=7).make_parents(150)
    second = PersonaFactory(seed=8).make_parents(150)

    for attribute in (
        "child_age",
        "disposable_budget_eur",
        "ai_attitude",
        "streaming_service",
        "screen_time_philosophy",
        "existing_devices",
    ):
        assert [getattr(parent, attribute) for parent in first] != [
            getattr(parent, attribute) for parent in second
        ]


def test_parent_population_retains_existing_contracts_and_diversity():
    parents = PersonaFactory(seed=7).make_parents(150)

    assert [parent.persona_id for parent in parents] == [f"parent-{index:03d}" for index in range(150)]
    assert len(parents) == 150
    assert len({parent.ai_attitude for parent in parents}) >= 4
    assert len({parent.streaming_service for parent in parents}) >= 4
    assert any(parent.privacy_concern >= 0.8 for parent in parents)
    assert any(parent.ai_attitude == "opposed" for parent in parents)
    assert all(parent.disposable_budget_eur >= 0 for parent in parents)
    assert validate_parent_population(parents) == []


def test_parent_dimensions_remain_marginally_balanced():
    parents = PersonaFactory(seed=7).make_parents(120)

    for values in (
        [parent.child_age for parent in parents],
        [parent.disposable_budget_eur for parent in parents],
        [parent.ai_attitude for parent in parents],
        [parent.streaming_service for parent in parents],
        [parent.screen_time_philosophy for parent in parents],
        [tuple(parent.existing_devices) for parent in parents],
    ):
        counts = {value: values.count(value) for value in set(values)}
        assert max(counts.values()) - min(counts.values()) <= 1


def test_parent_dimensions_are_not_mechanically_one_to_one_coupled():
    parents = PersonaFactory(seed=7).make_parents(120)

    assert len({(parent.child_age, parent.disposable_budget_eur) for parent in parents}) > 5
    assert len({(parent.ai_attitude, parent.streaming_service) for parent in parents}) > 4
    assert len({(parent.ai_attitude, parent.screen_time_philosophy) for parent in parents}) > 4
    assert len({(parent.streaming_service, tuple(parent.existing_devices)) for parent in parents}) > 12


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


def test_population_validators_report_missing_segments_and_invalid_budget():
    parents = [PersonaFactory(7).make_parents(1)[0].model_copy(update={
        "ai_attitude": "enthusiastic", "privacy_concern": 0, "disposable_budget_eur": -1,
    })]
    expected = {"missing AI-attitude diversity", "missing rejecting parent segment",
        "missing high-privacy segment", "negative household budget"}
    assert set(validate_parent_population(parents)) == expected
    assert set(validate_population(parents)) == expected
    assert "missing rejecting parent segment" in validate_population([])


def test_children_and_education_are_reproducible_for_same_seed():
    assert PersonaFactory(11).make_children(30) == PersonaFactory(11).make_children(30)
    assert PersonaFactory(11).make_education(20) == PersonaFactory(11).make_education(20)
