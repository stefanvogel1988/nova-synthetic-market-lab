import json

import pytest

from nova_lab import cli
from nova_lab.providers.deterministic import DeterministicEngine
from nova_lab.scoring import rubrics
from nova_lab.settings import LabSettings
from nova_lab.storage.jsonl import append_jsonl, read_jsonl


SMALL_RUN = LabSettings(parent_count=2, child_count=1, education_count=1)


def test_fixed_seed_persists_explicit_rubric_components_and_reproducible_scores(tmp_path):
    runs = [cli.run_pipeline(7, tmp_path, settings=SMALL_RUN) for _ in range(2)]
    rows = [read_jsonl(run.run_dir / "observations.jsonl") for run in runs]
    metrics = [[row["metrics"] for row in run_rows if "purchase_interest" in row["metrics"]]
               for run_rows in rows]
    assert metrics[0]
    for row_metrics in metrics[0]:
        assert rubrics.PARENT_WEIGHTS.keys() <= row_metrics.keys()
        assert "parent_product_score" in row_metrics
    assert metrics[0] == metrics[1]


@pytest.mark.parametrize("component", ["differentiation", "repeat_use"])
def test_pipeline_scores_use_each_generated_component(tmp_path, monkeypatch, component):
    class ComponentEngine(DeterministicEngine):
        value = 0.0

        def evaluate_parent(self, parent, variant, context):
            row = super().evaluate_parent(parent, variant, context)
            row.metrics[component] = self.value
            return row

    monkeypatch.setattr(cli, "DeterministicEngine", ComponentEngine)
    low = cli.run_pipeline(7, tmp_path, settings=SMALL_RUN)
    ComponentEngine.value = 100.0
    high = cli.run_pipeline(7, tmp_path, settings=SMALL_RUN)
    low_rows = read_jsonl(low.run_dir / "observations.jsonl")
    high_rows = read_jsonl(high.run_dir / "observations.jsonl")
    pairs = [(a, b) for a, b in zip(low_rows, high_rows)
             if "purchase_interest" in a["metrics"] and not a["objections"]]
    assert pairs
    for a, b in pairs:
        assert a["metrics"][component] == 0.0
        assert b["metrics"][component] == 100.0
        # Each final score is rounded to cents independently.
        assert b["metrics"]["parent_product_score"] - a["metrics"]["parent_product_score"] == pytest.approx(10.0, abs=0.011)


def test_rubric_weight_change_changes_persisted_scores_and_product_ranking(tmp_path, monkeypatch):
    # A pipeline ranking raw purchase interest leaves rubric changes inert.
    monkeypatch.setattr(rubrics, "PARENT_WEIGHTS", {"trust": 100})
    trust_run = cli.run_pipeline(7, tmp_path, settings=SMALL_RUN)
    monkeypatch.setattr(rubrics, "PARENT_WEIGHTS", {"price_fit": 100})
    price_run = cli.run_pipeline(7, tmp_path, settings=SMALL_RUN)

    trust_report = (trust_run.run_dir / "executive_report.md").read_text()
    price_report = (price_run.run_dir / "executive_report.md").read_text()
    assert trust_report != price_report
    trust_rows = read_jsonl(trust_run.run_dir / "observations.jsonl")
    price_rows = read_jsonl(price_run.run_dir / "observations.jsonl")
    assert any(a["metrics"]["parent_product_score"] != b["metrics"]["parent_product_score"]
               for a, b in zip(trust_rows, price_rows) if "purchase_interest" in a["metrics"])
    assert all(a["metrics"]["purchase_interest"] == b["metrics"]["purchase_interest"]
               for a, b in zip(trust_rows, price_rows) if "purchase_interest" in a["metrics"])
    assert "median judged parent/product score" in trust_report


def test_reports_can_rebuild_legacy_observations_without_judged_scores(tmp_path):
    # Existing persisted runs remain readable when the new metric is absent.
    result = cli.run_pipeline(7, tmp_path, settings=SMALL_RUN)
    path = result.run_dir / "observations.jsonl"
    rows = read_jsonl(path)
    for row in rows:
        row["metrics"].pop("parent_product_score", None)
    path.unlink()
    append_jsonl(path, rows)
    cli.generate_reports(result.run_dir)
    assert "median judged parent/product score" in (result.run_dir / "executive_report.md").read_text()


def test_pipeline_uses_supplied_judge_on_finalized_rows_and_consumes_its_scores(tmp_path):
    # Ignoring the replaceable JudgeEngine or its result must change real artifacts.
    class FixedJudge:
        def __init__(self):
            self.observations = []

        def score(self, observation):
            self.observations.append(observation)
            return {"parent_product_score": 12.5}

    judge = FixedJudge()
    result = cli.run_pipeline(7, tmp_path, settings=SMALL_RUN, judge=judge)
    rows = read_jsonl(result.run_dir / "observations.jsonl")
    parent_rows = [row for row in rows if "purchase_interest" in row["metrics"]]
    assert len(judge.observations) == len(parent_rows) > 0
    assert all(row["metrics"]["parent_product_score"] == 12.5 for row in parent_rows)
    assert all(row.selected_option in {"buy_nova", "competing_purchase", "defer"}
               for row in judge.observations if row.offered_option is not None)
    assert any(row.offered_option is not None for row in judge.observations)
    report = (result.run_dir / "executive_report.md").read_text()
    assert "median judged parent/product score 12.50/100" in report


def test_contradictory_synthetic_interest_and_decision_reach_evidence(tmp_path, monkeypatch):
    # High interest plus a budget-driven rejection must survive as counterevidence.
    class EnthusiasticEngine(DeterministicEngine):
        def evaluate_parent(self, parent, variant, context):
            row = super().evaluate_parent(parent, variant, context)
            return row.model_copy(update={
                "metrics": {**row.metrics, "purchase_interest": 90.0},
                "rationale": "Synthetic agent states high purchase interest (90/100).",
            })

    monkeypatch.setattr(cli, "DeterministicEngine", EnthusiasticEngine)
    result = cli.run_pipeline(7, tmp_path, settings=SMALL_RUN)
    rows = read_jsonl(result.run_dir / "observations.jsonl")
    rejected = [row for row in rows if row["metrics"].get("selected_nova") == 0]
    assert rejected
    assert all("preference_decision_contradiction" in row["objections"] for row in rejected)
    assert all("preference_decision_contradiction" not in row["objections"]
               for row in rows if row["metrics"].get("selected_nova") != 0)
    claims = json.loads(result.evidence_register_path.read_text())["claims"]
    pricing = next(claim for claim in claims if claim["category"] == "pricing")
    assert pricing["current_status"] == "CONTESTED"
    assert "preference_decision_contradiction" in pricing["counterevidence"]
    assert pricing["next_decision"] == "VALIDATE_WITH_HUMANS"
    assert all(claim["current_status"] != "PROVEN" for claim in claims)
    assert all(source["source_type"] == "synthetic_experiment"
               for claim in claims for source in claim["supporting_evidence"])
