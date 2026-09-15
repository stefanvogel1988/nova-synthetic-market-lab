from pathlib import Path

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


def test_report_accepts_an_existing_run_directory(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert result.exit_code == 0
    assert str(run_dir) in result.stdout
