from pathlib import Path

from nova_lab.experiments.registry import load_variants
from nova_lab.experiments.runner import ExperimentRunner, blinded_order
from nova_lab.models.experiment import ExperimentDefinition
from nova_lab.models.persona import ParentPersona
from nova_lab.providers.deterministic import DeterministicEngine
from nova_lab.storage.jsonl import append_jsonl, read_jsonl


def test_blinded_order_is_reproducible_but_not_source_order():
    source = ["A", "B", "C", "D", "E", "F"]

    first = blinded_order(source, seed=42, salt="p1")
    second = blinded_order(source, seed=42, salt="p1")

    assert first == second
    assert first != source


def test_runner_evaluates_one_parent_across_six_blinded_variants():
    parent = ParentPersona(
        persona_id="parent-1",
        child_age=6,
        child_count=1,
        disposable_budget_eur=250,
        price_sensitivity=0.5,
        ai_attitude="pragmatic",
        privacy_concern=0.4,
        subscription_tolerance=0.5,
        existing_devices=["speaker"],
        streaming_service="spotify",
        technical_confidence=0.5,
        education_orientation=0.7,
        convenience_orientation=0.6,
        screen_time_philosophy="limited",
        locale_type="suburban",
    )
    experiment = ExperimentDefinition(
        experiment_id="all-variants",
        family="concept",
        hypothesis="A blinded comparison is reproducible.",
        success_criteria="Each variant receives one observation.",
        scenario="parent evaluation",
        variant_ids=["A", "B", "C", "D", "E", "F"],
    )
    runner = ExperimentRunner(DeterministicEngine(seed=9), seed=42)

    observations = runner.run_parent_experiment(
        run_id="run-1",
        experiment=experiment,
        parents=[parent],
        variants=load_variants(Path("config/variants.yaml")),
        context={"price_eur": 179},
    )

    assert [observation.variant_id for observation in observations] == blinded_order(
        experiment.variant_ids, seed=42, salt=parent.persona_id
    )
    assert len(observations) == 6
    assert {observation.run_id for observation in observations} == {"run-1"}
    assert {observation.experiment_id for observation in observations} == {"all-variants"}
    assert all(observation.metrics for observation in observations)
    assert all(observation.rationale for observation in observations)


def test_jsonl_storage_round_trips_records_and_creates_parent_directory(tmp_path):
    path = tmp_path / "runs" / "observations.jsonl"
    records = [{"variant_id": "A", "interest": 67.2}, {"variant_id": "B", "interest": 59.1}]

    append_jsonl(path, records)

    assert read_jsonl(path) == records
