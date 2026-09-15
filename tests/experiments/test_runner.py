from pathlib import Path

from nova_lab.experiments.registry import load_variants
from nova_lab.experiments.runner import ExperimentRunner, blinded_order
from nova_lab.models.experiment import ExperimentDefinition
from nova_lab.models.experiment import ExperimentObservation
from nova_lab.personas.factory import PersonaFactory
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


def test_runner_hides_original_identity_from_provider_and_restores_mapping():
    class RecordingProvider:
        def __init__(self):
            self.seen = []

        def evaluate_parent(self, parent, variant, context):
            self.seen.append((variant, context))
            return ExperimentObservation(run_id=context["run_id"], experiment_id=context["experiment_id"],
                persona_id=parent.persona_id, variant_id=variant.variant_id,
                metrics={"trust": 10 if variant.privacy_first else 1})

    provider = RecordingProvider()
    originals = load_variants(Path("config/variants.yaml"))
    experiment = ExperimentDefinition(experiment_id="blind", family="privacy", hypothesis="h",
        success_criteria="s", scenario="s", variant_ids=list(originals))
    runner = ExperimentRunner(provider, 42)
    rows = runner.run_parent_experiment("r", experiment, PersonaFactory(1).make_parents(1), originals)
    assert {row.variant_id for row in rows} == set(originals)
    assert all(variant.variant_id not in originals for variant, _ in provider.seen)
    assert all(variant.label.startswith("Concept ") for variant, _ in provider.seen)
    assert all(variant.label not in {v.label for v in originals.values()} for variant, _ in provider.seen)
    assert all("variant_id" not in context and "label" not in context for _, context in provider.seen)
    assert all(row.metrics["trust"] == (10 if originals[row.variant_id].privacy_first else 1) for row in rows)
    assert all(row.blinded_variant_id == variant.variant_id for row, (variant, _) in zip(rows, provider.seen))


def test_jsonl_reads_utf8_even_when_locale_default_is_ascii(tmp_path, monkeypatch):
    path = tmp_path / "umlauts.jsonl"
    append_jsonl(path, [{"text": "Neugier für 179 €"}])
    original_read = Path.read_text

    def locale_read(self, encoding=None, **kwargs):
        return original_read(self, encoding=encoding or "ascii", **kwargs)

    monkeypatch.setattr(Path, "read_text", locale_read)
    assert read_jsonl(path) == [{"text": "Neugier für 179 €"}]
