"""Behavioral contracts for executed synthetic child sessions, not real children."""

from collections import defaultdict
import json

import pytest

from nova_lab.cli import generate_reports, run_pipeline
from nova_lab.settings import LabSettings
from nova_lab.storage.jsonl import read_jsonl


SITUATIONS = {
    "after_school", "bedtime", "weekend", "sibling_competition", "weak_wifi",
    "no_internet", "parent_busy", "child_bored", "sensitive_question", "music_only",
}
PERIODS = {"day_1", "day_3", "week_1", "week_2", "week_4"}
SMALL = LabSettings(parent_count=2, child_count=2, education_count=2)


def events_from(result):
    path = result.run_dir / "child_events.jsonl"
    assert path.exists(), "A completed run must persist executed child scenario events"
    rows = read_jsonl(path)
    assert rows, "Static personas and empty event files are insufficient"
    return rows


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    return run_pipeline(20260915, tmp_path_factory.mktemp("child-events"))


def test_full_run_executes_all_usage_situations_and_interaction_behaviors(full_run):
    # Omitting event dispatch or any planned situation/interaction must fail.
    events = events_from(full_run)
    children = read_jsonl(full_run.run_dir / "children.jsonl")
    assert {(e["persona_id"], e["variant_id"], e["period"], e["scenario_id"]) for e in events} == {
        (child["persona_id"], variant, period, scenario)
        for child in children for variant in ("B", "C", "E")
        for period in PERIODS for scenario in SITUATIONS
    }
    assert {e["kind"] for e in events} >= {
        "question", "asr_misunderstanding", "clarification", "explanation", "follow_up",
        "boredom", "misunderstanding", "refusal", "lapse", "reengagement", "adult_bridge", "music",
    }
    assert {e["domain"] for e in events} >= {
        "science", "math", "language", "animals", "body", "death_and_grief",
        "family_conflict", "religion", "politics", "health", "safety", "privacy",
    }
    assert all(e["synthetic"] is True for e in events)
    assert any(e["state_before"] != e["state_after"] for e in events)
    assert any(e["comprehension"] > 0 for e in events)


def test_event_associations_and_order_link_to_usage_and_run(full_run):
    # Cross-persona/run leakage, broken state chaining, or lost event references fail.
    events = events_from(full_run)
    groups = defaultdict(list)
    for event in events:
        assert event["run_id"] == full_run.run_dir.name
        assert event["experiment_id"] == "usage-v1"
        groups[(event["persona_id"], event["variant_id"], event["period"], event["scenario_id"])].append(event)
    for rows in groups.values():
        assert [e["sequence"] for e in rows] == list(range(1, len(rows) + 1))
        assert all(a["state_after"] == b["state_before"] for a, b in zip(rows, rows[1:]))
    assert len({e["event_id"] for e in events}) == len(events)
    for snapshot in read_jsonl(full_run.run_dir / "usage.jsonl"):
        matching = [e for e in events if all(e[key] == snapshot[key] for key in (
            "run_id", "experiment_id", "persona_id", "variant_id", "period",
        ))]
        assert set(snapshot["event_ids"]) == {e["event_id"] for e in matching}
        assert snapshot["scenario_count"] == 10


def test_event_evaluation_changes_usage_evidence_and_report(tmp_path):
    # A decorative event artifact that never influences the existing pipeline fails.
    baseline = run_pipeline(7, tmp_path, settings=SMALL)
    events_from(baseline)
    from nova_lab.child.events import DeterministicChildEngine

    class NoUsefulInteractions(DeterministicChildEngine):
        def simulate(self, *args, **kwargs):
            return [event.model_copy(update={"useful": False, "comprehension": 0.0})
                    for event in super().simulate(*args, **kwargs)]

    changed = run_pipeline(7, tmp_path, settings=SMALL, child_engine=NoUsefulInteractions())
    first = read_jsonl(baseline.run_dir / "usage.jsonl")
    second = read_jsonl(changed.run_dir / "usage.jsonl")
    assert sum(row["useful_interactions"] for row in first) > 0
    assert all(row["useful_interactions"] == 0 for row in second)
    observations = read_jsonl(changed.run_dir / "observations.jsonl")
    assert all(row["metrics"]["useful_interactions"] == 0 for row in observations
               if row["experiment_id"] == "usage-v1")
    def usage_claim(result):
        evidence = json.loads(result.evidence_register_path.read_text())
        return next(c for c in evidence["claims"] if c["claim_id"] == "usage-v1")
    assert usage_claim(baseline)["claim_text"] != usage_claim(changed)["claim_text"]
    assert usage_claim(changed)["current_status"] != "PROVEN"
    report = (changed.run_dir / "executive_report.md").read_text()
    assert "median modeled useful interactions=0.00" in report
    assert "child interaction events" in report.lower()
    assert "not observed child" in report.lower()


def test_fixed_seed_reproduces_event_semantics_in_distinct_runs(tmp_path):
    # Seeding with operational UUIDs or time changes would fail this comparison.
    first = run_pipeline(17, tmp_path, settings=SMALL)
    first_events = events_from(first)
    second = run_pipeline(17, tmp_path, settings=SMALL)
    second_events = events_from(second)
    assert first.run_dir != second.run_dir
    assert [{k: v for k, v in e.items() if k != "run_id"} for e in first_events] == [
        {k: v for k, v in e.items() if k != "run_id"} for e in second_events
    ]


def test_connectivity_and_sensitive_events_produce_usage_risk(full_run):
    # Static benign answers for offline or sensitive questions would fail.
    events = events_from(full_run)
    offline = [e for e in events if e["scenario_id"] == "no_internet"]
    assert any(e["kind"] == "refusal" and e["abandonment_reason"] == "no_internet" for e in offline)
    assert not any(e["useful"] for e in offline)
    sensitive = [e for e in events if e["scenario_id"] == "sensitive_question"]
    assert any(e["kind"] == "adult_bridge" and e["state_after"]["needs_parent"] for e in sensitive)
    assert not any(e["kind"] == "explanation" for e in sensitive)
    music = [e for e in events if e["scenario_id"] == "music_only"]
    assert any(e["kind"] == "music" for e in music)
    assert not any(e["kind"] == "follow_up" for e in music)


@pytest.mark.parametrize("mutation", ["run_id", "persona_id", "drop_event", "synthetic", "sequence", "missing_manifest_count"])
def test_report_rejects_corrupt_child_events_before_rewriting(tmp_path, mutation):
    # New child-event inputs must preserve the existing artifact-integrity boundary.
    result = run_pipeline(7, tmp_path, settings=SMALL)
    events = events_from(result)
    before = (result.run_dir / "executive_report.md").read_bytes()
    if mutation == "missing_manifest_count":
        evidence_path = result.evidence_register_path
        evidence = json.loads(evidence_path.read_text())
        del evidence["artifact_counts"]["child_events"]
        evidence_path.write_text(json.dumps(evidence))
    elif mutation == "drop_event":
        events.pop()
    else:
        events[0][mutation] = {"run_id": "other-run", "persona_id": "not-a-child",
                               "synthetic": False, "sequence": 0}[mutation]
    (result.run_dir / "child_events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n"
    )
    with pytest.raises(ValueError, match="incomplete or invalid run"):
        generate_reports(result.run_dir)
    assert (result.run_dir / "executive_report.md").read_bytes() == before
