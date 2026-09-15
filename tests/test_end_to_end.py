import json
from math import isclose
from pathlib import Path

from typer.testing import CliRunner

from nova_lab.models.experiment import ExperimentObservation
from nova_lab.models.persona import ChildPersona, EducationPersona, ParentPersona, RedTeamPersona
from nova_lab.storage.jsonl import read_jsonl


ARTIFACTS = {
    "parents.jsonl", "children.jsonl", "education.jsonl", "red_team.jsonl",
    "observations.jsonl", "usage.jsonl", "safety.jsonl", "evidence.json",
    "executive_report.md", "investor_summary.md",
}


def test_v1_acceptance_run(tmp_path: Path):
    # Missing family dispatch or fabricated result metadata must fail on artifacts.
    from nova_lab.cli import PipelineResult, run_pipeline

    result = run_pipeline(seed=20260915, output_dir=tmp_path)

    assert isinstance(result, PipelineResult)
    assert set(result.variant_ids) == {"A", "B", "C", "D", "E", "F"}
    assert len(result.experiment_families) >= 5
    assert result.usage_periods == ["day_1", "day_3", "week_1", "week_2", "week_4"]
    assert result.red_team_has_pre_post_scores is True
    assert result.safety_report_has_critical_failure_field is True
    assert result.evidence_register_path.exists()
    assert result.investor_summary_path.exists()
    assert "does not prove product-market fit" in result.investor_summary_path.read_text().lower()
    assert ARTIFACTS <= {path.name for path in result.run_dir.iterdir()}
    assert len(read_jsonl(result.run_dir / "parents.jsonl")) == 150
    assert len(read_jsonl(result.run_dir / "children.jsonl")) == 30
    assert len(read_jsonl(result.run_dir / "education.jsonl")) == 20
    for filename, model in (
        ("parents.jsonl", ParentPersona),
        ("children.jsonl", ChildPersona),
        ("education.jsonl", EducationPersona),
    ):
        assert all(model.model_validate(row) for row in read_jsonl(result.run_dir / filename))
    red_team = read_jsonl(result.run_dir / "red_team.jsonl")
    assert len(red_team) == 12
    assert all(RedTeamPersona.model_validate(row) for row in red_team)
    assert all("pre_score" in row and "post_score" in row and row["finding"] for row in red_team)
    assert len({row["pre_score"] for row in red_team}) > 1
    assert len({row["post_score"] for row in red_team}) > 1
    for row in red_team:
        assert len(row["peer_critiques"]) == 11
        assert all(peer["persona_id"] != row["persona_id"] for peer in row["peer_critiques"])
        assert row["post_score"] < row["pre_score"]
        assert isclose(row["post_score"], max(0, row["pre_score"] + sum(
            peer["adjustment"] for peer in row["peer_critiques"]
        )))
    observations = read_jsonl(result.run_dir / "observations.jsonl")
    assert all(ExperimentObservation.model_validate(row) for row in observations)
    assert {row["variant_id"] for row in observations} == {"A", "B", "C", "D", "E", "F"}
    assert {row["experiment_id"] for row in observations} >= {
        "positioning-v1", "pricing-v1", "privacy-v1", "learning-v1", "usage-v1", "education-v1",
    }
    assert all(row["run_id"] == result.run_dir.name for row in observations)
    usage = read_jsonl(result.run_dir / "usage.jsonl")
    assert len(usage) == 30 * 3 * 5
    assert {row["period"] for row in usage} == set(result.usage_periods)
    children = read_jsonl(result.run_dir / "children.jsonl")
    assert {child["age"] for child in children} == {5, 6, 7, 8, 9}
    assert {(row["persona_id"], row["variant_id"], row["period"]) for row in usage} == {
        (child["persona_id"], variant_id, period)
        for child in children
        for variant_id in ("B", "C", "E")
        for period in result.usage_periods
    }
    safety = read_jsonl(result.run_dir / "safety.jsonl")
    assert safety and all("critical_failure" in row for row in safety)
    assert any(row["critical_failure"] and row["negative_control"] for row in safety)
    evidence = json.loads(result.evidence_register_path.read_text())
    assert evidence["claims"] and evidence["segment_summaries"]
    assert all(claim["current_status"] != "PROVEN" for claim in evidence["claims"])
    report = (result.run_dir / "executive_report.md").read_text()
    assert "critical_failure" in report
    assert "fixture" in report.lower()
    assert "No ranking recorded" not in report
    assert "No segment analysis recorded" not in report
    assert "No investment-committee findings recorded" not in report


def normalized_artifacts(run_dir: Path) -> dict:
    # Only operational run_id is excluded; every metric, status and report stays.
    def normalize(value):
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items() if key != "run_id"}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    return {
        name: normalize(read_jsonl(run_dir / name)) if name.endswith(".jsonl")
        else normalize(json.loads((run_dir / name).read_text())) if name.endswith(".json")
        else (run_dir / name).read_text()
        for name in sorted(ARTIFACTS)
    }


def test_fixed_seed_reproduces_all_semantic_artifacts_in_distinct_runs(tmp_path: Path):
    # Time-derived IDs must neither alter model noise nor overwrite a prior run.
    from nova_lab.cli import run_pipeline

    first = run_pipeline(seed=20260915, output_dir=tmp_path)
    original = normalized_artifacts(first.run_dir)
    second = run_pipeline(seed=20260915, output_dir=tmp_path)

    assert first.run_dir != second.run_dir
    assert normalized_artifacts(first.run_dir) == original
    assert normalized_artifacts(second.run_dir) == original


def test_run_command_executes_pipeline_and_honors_population_settings(tmp_path: Path):
    # A CLI that merely prints readiness, or discards configured counts, is broken.
    from nova_lab.cli import app

    config = tmp_path / "lab.yaml"
    config.write_text(
        "seed: 20260915\nparent_count: 2\nchild_count: 2\neducation_count: 2\n"
        f"output_dir: {tmp_path / 'outputs'}\n"
    )
    result = CliRunner().invoke(app, ["run", "--config", str(config), "--provider", "deterministic"])

    assert result.exit_code == 0, result.output
    run_dir = Path(result.stdout.strip())
    assert run_dir.is_dir()
    assert ARTIFACTS <= {path.name for path in run_dir.iterdir()}
    assert len(read_jsonl(run_dir / "parents.jsonl")) == 2
    assert len(read_jsonl(run_dir / "children.jsonl")) == 2
    assert len(read_jsonl(run_dir / "education.jsonl")) == 2
