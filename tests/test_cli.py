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


REPORT_RUN_ID_ARTIFACTS = (
    ("usage",),
    ("red_team",),
    ("safety",),
    ("usage", "red_team"),
    ("usage", "safety"),
    ("red_team", "safety"),
    ("usage", "red_team", "safety"),
)


@pytest.fixture(scope="module")
def completed_run_for_report_integrity(tmp_path_factory):
    from nova_lab.cli import run_pipeline
    from nova_lab.settings import LabSettings

    return run_pipeline(
        7,
        tmp_path_factory.mktemp("report-integrity"),
        settings=LabSettings(parent_count=2, child_count=2, education_count=2),
    ).run_dir


def copied_completed_run(source: Path, destination: Path) -> Path:
    run_dir = destination / source.name
    shutil.copytree(source, run_dir)
    return run_dir


def test_validate_command_succeeds():
    result = CliRunner().invoke(app, ["validate"])

    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


REQUIRED_EXPERIMENT_FAMILIES = (
    "positioning",
    "pricing",
    "privacy",
    "learning",
    "usage",
    "education",
)


def _complete_experiment_config() -> list[dict]:
    return yaml.safe_load(Path("config/experiments.yaml").read_text())["experiments"]


def _validate_experiments(tmp_path: Path, experiments: list[dict]):
    tmp_path.mkdir(parents=True, exist_ok=True)
    for name in ("lab", "variants", "safety"):
        shutil.copyfile(Path("config") / f"{name}.yaml", tmp_path / f"{name}.yaml")
    experiment_path = tmp_path / "experiments.yaml"
    experiment_path.write_text(yaml.safe_dump({"experiments": experiments}), encoding="utf-8")
    return CliRunner().invoke(
        app,
        [
            "validate",
            "--config", str(tmp_path / "lab.yaml"),
            "--variants", str(tmp_path / "variants.yaml"),
            "--experiments", str(experiment_path),
            "--safety", str(tmp_path / "safety.yaml"),
        ],
    )


def test_validate_accepts_a_complete_v1_experiment_family_configuration(tmp_path: Path):
    outcome = _validate_experiments(tmp_path, _complete_experiment_config())

    assert outcome.exit_code == 0, outcome.output
    assert "configuration valid" in outcome.output.lower()


@pytest.mark.parametrize("missing_family", REQUIRED_EXPERIMENT_FAMILIES)
def test_validate_rejects_each_missing_required_v1_experiment_family(
    tmp_path: Path, missing_family: str
):
    experiments = [
        experiment
        for experiment in _complete_experiment_config()
        if experiment["family"] != missing_family
    ]

    outcome = _validate_experiments(tmp_path, experiments)

    assert outcome.exit_code != 0
    assert "missing required experiment families" in outcome.output.lower()
    assert missing_family in outcome.output


def test_validate_reports_all_missing_required_v1_experiment_families(tmp_path: Path):
    missing_families = {"pricing", "usage", "education"}
    experiments = [
        experiment
        for experiment in _complete_experiment_config()
        if experiment["family"] not in missing_families
    ]

    outcome = _validate_experiments(tmp_path, experiments)

    assert outcome.exit_code != 0
    assert "missing required experiment families" in outcome.output.lower()
    for family in missing_families:
        assert family in outcome.output


def test_validate_keeps_extra_known_and_unknown_family_behavior_compatible(tmp_path: Path):
    experiments = _complete_experiment_config()
    experiments.append({**experiments[0], "experiment_id": "positioning-extra"})

    extra_outcome = _validate_experiments(tmp_path / "extra", experiments)
    unknown_outcome = _validate_experiments(
        tmp_path / "unknown",
        [{**experiments[0], "family": "unrecognized"}, *experiments[1:]],
    )

    assert extra_outcome.exit_code == 0, extra_outcome.output
    assert unknown_outcome.exit_code != 0
    assert "unsupported experiment family" in unknown_outcome.output.lower()


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


def test_executive_report_shows_education_usage_and_safety_risk_distributions(tmp_path):
    from nova_lab.cli import run_pipeline
    from nova_lab.settings import LabSettings

    result = run_pipeline(
        7,
        tmp_path,
        settings=LabSettings(parent_count=2, child_count=2, education_count=2),
    )
    report = (result.run_dir / "executive_report.md").read_text(encoding="utf-8")
    observations = read_jsonl(result.run_dir / "observations.jsonl")
    education = [row for row in observations if row["experiment_id"] == "education-v1"]
    education_fit = sum(
        row["metrics"]["usefulness"] >= 65
        and row["metrics"]["administration_burden"] <= 40
        for row in education
    )
    education_blocked = len(education) - education_fit
    usefulness_blockers = sum(row["metrics"]["usefulness"] < 65 for row in education)
    burden_blockers = sum(
        row["metrics"]["administration_burden"] > 40 for row in education
    )

    assert (
        f"Modeled education adoption/fit: {education_fit}/{len(education)} "
        "scenario-persona results meet the configured usefulness and administration thresholds"
    ) in report
    assert f"Modeled education rejection/blocking: {education_blocked}/{len(education)}" in report
    assert (
        f"Central modeled blockers: usefulness below 65/100={usefulness_blockers}/{len(education)}; "
        f"administration burden above 40/100={burden_blockers}/{len(education)}"
    ) in report

    usage = read_jsonl(result.run_dir / "usage.jsonl")
    for period in ("day_1", "day_3", "week_1", "week_2", "week_4"):
        rows = [row for row in usage if row["period"] == period]
        engaged_at_checkpoint = sum(
            row["session_state"]["mode"] == "engaged" for row in rows
        )
        lapsed = sum(row["session_state"]["mode"] == "lapsed" for row in rows)
        assert (
            f"{period}: engaged at checkpoint sessions={engaged_at_checkpoint}/{len(rows)}; "
            f"lapsed sessions={lapsed}/{len(rows)}"
        ) in report
    assert "Negative usage signal distribution across 30-day snapshots: lapsed=" in report

    safety = read_jsonl(result.run_dir / "safety.jsonl")
    critical_categories = sorted({
        row["category"] for row in safety if row["critical_failure"]
    })
    assert "Critical-risk fixture categories (injected negative controls):" in report
    for category in critical_categories:
        rows = [row for row in safety if row["category"] == category]
        critical = sum(row["critical_failure"] for row in rows)
        assert f"{category}={critical}/{len(rows)}" in report


def test_report_labels_lapse_to_reengagement_as_checkpoint_state(tmp_path):
    from nova_lab.cli import run_pipeline
    from nova_lab.settings import LabSettings

    result = run_pipeline(
        7,
        tmp_path,
        settings=LabSettings(parent_count=2, child_count=2, education_count=2),
    )
    usage_path = result.run_dir / "usage.jsonl"
    usage = read_jsonl(usage_path)
    persona_id, variant_id = usage[0]["persona_id"], usage[0]["variant_id"]
    week_2 = next(
        row for row in usage
        if (row["persona_id"], row["variant_id"], row["period"])
        == (persona_id, variant_id, "week_2")
    )
    week_4 = next(
        row for row in usage
        if (row["persona_id"], row["variant_id"], row["period"])
        == (persona_id, variant_id, "week_4")
    )
    week_2["session_state"]["mode"] = "lapsed"
    week_2["useful_interactions"] = 0
    week_4["session_state"]["mode"] = "engaged"
    week_4["useful_interactions"] = 1
    usage_path.write_text(
        "\n".join(json.dumps(row) for row in usage) + "\n", encoding="utf-8"
    )

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(result.run_dir)])
    report = (result.run_dir / "executive_report.md").read_text(encoding="utf-8")

    assert outcome.exit_code == 0, outcome.output
    assert "week_2: engaged at checkpoint sessions=" in report
    assert "week_4: engaged at checkpoint sessions=" in report
    assert "retained engaged sessions" not in report


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


def test_report_accepts_persisted_artifacts_with_the_evidence_run_id(
    tmp_path, completed_run_for_report_integrity
):
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    evidence_run_id = json.loads((run_dir / "evidence.json").read_text())["run_id"]

    for filename in ("usage", "red_team", "safety"):
        path = run_dir / f"{filename}.jsonl"
        rows = read_jsonl(path)
        for row in rows:
            row["run_id"] = evidence_run_id
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code == 0, outcome.output


@pytest.mark.parametrize("artifact_names", REPORT_RUN_ID_ARTIFACTS)
def test_report_rejects_persisted_artifact_run_id_combinations_before_rendering(
    tmp_path, completed_run_for_report_integrity, artifact_names
):
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    report = run_dir / "executive_report.md"
    before = report.read_bytes()
    for filename in artifact_names:
        path = run_dir / f"{filename}.jsonl"
        rows = read_jsonl(path)
        rows[0]["run_id"] = "other-completed-run"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "mixed run identifiers" in outcome.output.lower()
    assert report.read_bytes() == before


@pytest.mark.parametrize("artifact_names", REPORT_RUN_ID_ARTIFACTS)
def test_report_rejects_missing_persisted_artifact_run_id_combinations_before_rendering(
    tmp_path, completed_run_for_report_integrity, artifact_names
):
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    report = run_dir / "executive_report.md"
    before = report.read_bytes()
    for filename in artifact_names:
        path = run_dir / f"{filename}.jsonl"
        rows = read_jsonl(path)
        del rows[0]["run_id"]
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "missing run identifier" in outcome.output.lower()
    assert report.read_bytes() == before


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
