from pathlib import Path
import json
import shutil

import pytest
import yaml

from typer.testing import CliRunner

from nova_lab.cli import app
from nova_lab.models.persona import (
    ChildPersona,
    EducationPersona,
    ParentPersona,
    RedTeamPersona,
)
from nova_lab.storage.jsonl import read_jsonl


def test_validate_command_succeeds():
    result = CliRunner().invoke(app, ["validate"])

    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_generate_writes_schema_valid_populations_to_new_run_directory(
    tmp_path: Path,
):
    config = tmp_path / "lab.yaml"
    config.write_text(
        "seed: 7\n"
        "parent_count: 2\n"
        "child_count: 2\n"
        "education_count: 2\n"
        "red_team_count: 2\n"
        f"output_dir: {tmp_path / 'outputs'}\n"
    )

    result = CliRunner().invoke(app, ["generate", "--config", str(config)])

    assert result.exit_code == 0
    run_dir = Path(result.stdout.strip())
    assert run_dir.is_dir()
    assert len(read_jsonl(run_dir / "parents.jsonl")) == 2
    assert len(read_jsonl(run_dir / "children.jsonl")) == 2
    assert len(read_jsonl(run_dir / "education.jsonl")) == 2
    assert len(read_jsonl(run_dir / "red_team.jsonl")) == 12
    assert all(ParentPersona.model_validate(row) for row in read_jsonl(run_dir / "parents.jsonl"))
    assert all(ChildPersona.model_validate(row) for row in read_jsonl(run_dir / "children.jsonl"))
    assert all(
        EducationPersona.model_validate(row) for row in read_jsonl(run_dir / "education.jsonl")
    )
    assert all(
        RedTeamPersona.model_validate(row) for row in read_jsonl(run_dir / "red_team.jsonl")
    )


def test_run_rejects_non_deterministic_provider(tmp_path: Path):
    config = tmp_path / "lab.yaml"
    config.write_text(f"output_dir: {tmp_path / 'outputs'}\n")

    result = CliRunner().invoke(
        app, ["run", "--config", str(config), "--provider", "paid-api"]
    )

    assert result.exit_code != 0
    assert "deterministic only" in result.output.lower()


def test_report_rejects_an_incomplete_run_directory(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert result.exit_code != 0
    assert "incomplete" in result.output.lower()


def test_report_regenerates_from_saved_artifacts_without_simulation(tmp_path, monkeypatch):
    from nova_lab import cli
    from nova_lab.settings import LabSettings
    result = cli.run_pipeline(7, tmp_path, settings=LabSettings(parent_count=2, child_count=2, education_count=2))
    names = ("executive_report.md", "investor_summary.md")
    expected = {name: (result.run_dir / name).read_text() for name in names}
    for name in names:
        (result.run_dir / name).unlink()

    def forbid_simulation(*args, **kwargs):
        raise AssertionError("report must use persisted artifacts")

    monkeypatch.setattr(cli, "run_pipeline", forbid_simulation)
    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(result.run_dir)])
    assert outcome.exit_code == 0, outcome.output
    assert all((result.run_dir / name).exists() for name in names)
    assert {name: (result.run_dir / name).read_text() for name in names} == expected
    (result.run_dir / "observations.jsonl").write_text("", encoding="utf-8")
    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(result.run_dir)])
    assert outcome.exit_code != 0
    assert "incomplete" in outcome.output.lower()


def test_report_rejects_partially_truncated_run_before_rewriting_reports(tmp_path):
    from nova_lab.cli import run_pipeline
    from nova_lab.settings import LabSettings
    result = run_pipeline(7, tmp_path, settings=LabSettings(parent_count=2, child_count=2, education_count=2))
    report = result.run_dir / "executive_report.md"
    before = report.read_bytes()
    observations = result.run_dir / "observations.jsonl"
    observations.write_text("\n".join(observations.read_text().splitlines()[1:]) + "\n", encoding="utf-8")
    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(result.run_dir)])
    assert outcome.exit_code != 0
    assert "incomplete" in outcome.output.lower()
    assert report.read_bytes() == before


@pytest.mark.parametrize(("filename", "field", "value"), [
    ("safety", "actual", "invalid-class"),
    ("red_team", "rejection_bias", 2),
    ("usage", "useful_interactions", "not-a-number"),
])
def test_report_rejects_invalid_persisted_schemas(tmp_path, filename, field, value):
    from nova_lab.cli import run_pipeline
    from nova_lab.settings import LabSettings
    result = run_pipeline(7, tmp_path, settings=LabSettings(parent_count=2, child_count=2, education_count=2))
    path = result.run_dir / f"{filename}.jsonl"
    rows = read_jsonl(path)
    rows[0][field] = value
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(result.run_dir)])
    assert outcome.exit_code != 0
    assert "invalid run" in outcome.output.lower()


def test_validate_default_command_loads_actual_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "lab.yaml").write_text("parent_count: 0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    outcome = CliRunner().invoke(app, ["validate"])
    assert outcome.exit_code == 1
    assert "parent_count" in outcome.output


@pytest.mark.parametrize(("target", "mutation", "message"), [
    ("lab", "invalid_count", "parent_count"),
    ("experiments", "missing_variant", "variant"),
    ("experiments", "blank_hypothesis", "hypothesis"),
    ("experiments", "blank_success", "success_criteria"),
    ("experiments", "duplicate_id", "duplicate"),
    ("experiments", "unknown_family", "family"),
    ("variants", "duplicate_id", "duplicate"),
    ("variants", "missing_description", "description"),
    ("safety", "bad_class", "expected"),
])
def test_validate_inspects_config_schemas_and_registry_references(tmp_path, target, mutation, message):
    for name in ("lab", "experiments", "variants", "safety"):
        shutil.copyfile(Path("config") / f"{name}.yaml", tmp_path / f"{name}.yaml")
    path = tmp_path / f"{target}.yaml"
    data = yaml.safe_load(path.read_text())
    if mutation == "invalid_count":
        data["parent_count"] = 0
    elif mutation == "missing_variant":
        data["experiments"][0]["variant_ids"] = ["missing"]
    elif mutation in {"blank_hypothesis", "blank_success"}:
        data["experiments"][0]["hypothesis" if mutation == "blank_hypothesis" else "success_criteria"] = " "
    elif mutation == "duplicate_id":
        data[target].append(data[target][0])
    elif mutation == "unknown_family":
        data["experiments"][0]["family"] = "unknown"
    elif mutation == "missing_description":
        del data["variants"][0]["description"]
    else:
        data["cases"][0]["expected"] = "unsafe"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    outcome = CliRunner().invoke(app, ["validate", "--config", str(tmp_path / "lab.yaml"),
        "--variants", str(tmp_path / "variants.yaml"), "--experiments", str(tmp_path / "experiments.yaml"),
        "--safety", str(tmp_path / "safety.yaml")])
    assert outcome.exit_code != 0
    assert "configuration invalid" in outcome.output.lower()
    assert message in outcome.output.lower()


def test_same_family_experiments_keep_separate_evidence_and_paired_comparisons(tmp_path, monkeypatch):
    from nova_lab import cli
    from nova_lab.settings import LabSettings
    original = cli.load_experiments

    def with_extra(path):
        experiments = original(path)
        experiments.append(experiments[0].model_copy(update={"experiment_id": "positioning-a-only", "variant_ids": ["A"]}))
        return experiments

    monkeypatch.setattr(cli, "load_experiments", with_extra)
    result = cli.run_pipeline(7, tmp_path, settings=LabSettings(parent_count=2, child_count=2, education_count=2))
    evidence = json.loads(result.evidence_register_path.read_text())
    claims = {claim["claim_id"]: claim for claim in evidence["claims"]}
    assert "48 synthetic scenarios" in claims["positioning-v1"]["claim_text"]
    assert "8 synthetic scenarios" in claims["positioning-a-only"]["claim_text"]
    assert evidence["segment_summaries"]["enthusiastic"]["n"] == 28
    assert "paired" in claims["learning-v1"]["claim_text"].lower()
    assert "delta" in claims["privacy-v1"]["claim_text"].lower()
    assert "unfavorable" in claims["learning-v1"]["claim_text"].lower()
