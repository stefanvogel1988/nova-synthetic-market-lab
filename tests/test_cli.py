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


@pytest.mark.parametrize(("mutation", "message"), [
    ("foreign_persona", "persona"),
    ("wrong_population", "persona"),
    ("unknown_experiment", "experiment"),
    ("unknown_variant", "variant"),
    ("wrong_experiment_variant", "variant"),
    ("invalid_positioning_option", "option"),
    ("invalid_privacy_option", "option"),
    ("invalid_learning_option", "option"),
    ("invalid_usage_option", "option"),
    ("invalid_education_option", "option"),
    ("invalid_pricing_offer", "option"),
    ("invalid_pricing_choice", "choice"),
    ("wrong_parent_pricing_choice", "choice"),
    ("unexpected_offer", "option"),
    ("duplicate", "duplicate"),
    ("duplicate_pricing_offer_with_different_choice", "duplicate"),
    ("missing", "missing"),
    ("extra", "persona"),
    ("wrong_run", "run"),
    ("invalid_registry_variant", "variant"),
    ("duplicate_registry_experiment", "duplicate"),
])
def test_report_rejects_invalid_observation_sets_before_rewriting(
    tmp_path, completed_run_for_report_integrity, mutation, message
):
    # Checking counts alone misses substitutions and truncation with updated metadata.
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "observations.jsonl"
    rows = read_jsonl(path)
    evidence_path = run_dir / "evidence.json"
    evidence = json.loads(evidence_path.read_text())
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}
    target = rows[0]
    if mutation == "foreign_persona":
        target["persona_id"] = "foreign-parent"
    elif mutation == "wrong_population":
        target["persona_id"] = read_jsonl(run_dir / "children.jsonl")[0]["persona_id"]
    elif mutation == "unknown_experiment":
        target["experiment_id"] = "foreign-experiment"
    elif mutation == "unknown_variant":
        target["variant_id"] = "foreign-variant"
    elif mutation == "wrong_experiment_variant":
        next(row for row in rows if row["experiment_id"] == "pricing-v1")["variant_id"] = "A"
    elif mutation.startswith("invalid_") and mutation.endswith("_option"):
        family = mutation.removeprefix("invalid_").removesuffix("_option")
        next(row for row in rows if row["experiment_id"] == f"{family}-v1")["selected_option"] = "foreign-option"
    elif mutation in {"invalid_pricing_offer", "invalid_pricing_choice", "wrong_parent_pricing_choice"}:
        target = next(row for row in rows if row["experiment_id"] == "pricing-v1")
        if mutation == "invalid_pricing_offer":
            target["offered_option"] = "999/999"
        elif mutation == "invalid_pricing_choice":
            target["selected_option"] = "foreign-choice"
        else:
            parent = next(row for row in read_jsonl(run_dir / "parents.jsonl")
                          if row["persona_id"] == target["persona_id"])
            target["selected_option"] = "defer" if parent["existing_devices"] else "competing_purchase"
    elif mutation == "unexpected_offer":
        target["offered_option"] = "149/0"
    elif mutation == "duplicate":
        rows[1] = dict(rows[0])
    elif mutation == "duplicate_pricing_offer_with_different_choice":
        target = next(row for row in rows if row["experiment_id"] == "pricing-v1")
        parent = next(row for row in read_jsonl(run_dir / "parents.jsonl")
                      if row["persona_id"] == target["persona_id"])
        other_choice = "buy_nova" if target["selected_option"] != "buy_nova" else (
            "competing_purchase" if parent["existing_devices"] else "defer"
        )
        rows.append({**target, "selected_option": other_choice})
    elif mutation == "missing":
        rows.pop(0)
    elif mutation == "extra":
        rows.append({**target, "persona_id": "extra-parent"})
    elif mutation == "wrong_run":
        target["run_id"] = "foreign-run"
    elif mutation == "invalid_registry_variant":
        evidence["experiments"][0]["variant_ids"].append("foreign-variant")
    elif mutation == "duplicate_registry_experiment":
        evidence["experiments"].append(dict(evidence["experiments"][0]))
    else:
        raise AssertionError(f"unhandled mutation: {mutation}")
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    evidence["artifact_counts"]["observations"] = len(rows)
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0, "invalid observation set was accepted"
    assert "incomplete or invalid run" in outcome.output.lower()
    assert message in outcome.output.lower()
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


def test_report_accepts_complete_observation_set_in_any_order(
    tmp_path, completed_run_for_report_integrity
):
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "observations.jsonl"
    rows = read_jsonl(path)
    path.write_text("\n".join(json.dumps(row) for row in reversed(rows)) + "\n", encoding="utf-8")
    before = path.read_bytes()

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code == 0, outcome.output
    assert path.read_bytes() == before


def test_validate_command_succeeds():
    result = CliRunner().invoke(app, ["validate"])

    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


@pytest.mark.parametrize("mutation", [
    "pre_out_of_bounds", "post_out_of_bounds", "unknown_finding", "wrong_finding_persona",
    "unknown_persona", "wrong_persona", "wrong_role", "wrong_rejection_bias",
    "pre_mismatch", "post_mismatch", "unknown_peer", "missing_peer", "duplicate_peer",
    "critique_adjustment", "critique_severity", "critique_rejection_issue", "missing_critiques",
    "duplicate", "missing", "extra", "committee_pre", "committee_post", "committee_member",
])
def test_report_rejects_inconsistent_red_team_records_before_rewriting(
    tmp_path, completed_run_for_report_integrity, mutation
):
    # Trusting standalone persona/finding schemas misses inconsistent complete records.
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "red_team.jsonl"
    rows = read_jsonl(path)
    row = rows[0]
    evidence_path = run_dir / "evidence.json"
    evidence = json.loads(evidence_path.read_text())
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}
    if mutation in {"pre_out_of_bounds", "post_out_of_bounds"}:
        row[mutation.split("_")[0] + "_score"] = 9000
    elif mutation == "unknown_finding":
        row["finding"]["persona_id"] = "unknown-finding"
    elif mutation == "wrong_finding_persona":
        row["finding"]["persona_id"] = rows[1]["persona_id"]
    elif mutation == "unknown_persona":
        row["persona_id"] = "foreign-persona"
    elif mutation == "wrong_persona":
        row["persona_id"] = rows[1]["persona_id"]
    elif mutation == "wrong_role":
        row["role"] = rows[1]["role"]
    elif mutation == "wrong_rejection_bias":
        row["rejection_bias"] = 0
    elif mutation in {"pre_mismatch", "post_mismatch"}:
        row[mutation.split("_")[0] + "_score"] += 1
    elif mutation == "unknown_peer":
        row["peer_critiques"][0]["persona_id"] = "foreign-peer"
    elif mutation == "missing_peer":
        row["peer_critiques"].pop()
    elif mutation == "duplicate_peer":
        row["peer_critiques"][1] = dict(row["peer_critiques"][0])
    elif mutation in {"critique_adjustment", "critique_severity"}:
        row["peer_critiques"][0][mutation.removeprefix("critique_")] += 0.1
    elif mutation == "critique_rejection_issue":
        row["peer_critiques"][0]["rejection_issue"] = "invented peer contradiction"
    elif mutation == "missing_critiques":
        del row["peer_critiques"]
    elif mutation == "duplicate":
        rows[1] = dict(row)
    elif mutation == "missing":
        rows.pop()
    elif mutation == "extra":
        rows.append({**row, "persona_id": "extra-member"})
    elif mutation in {"committee_pre", "committee_post"}:
        evidence["investment_committee"][mutation.removeprefix("committee_") + "_scores"][row["persona_id"]] += 1
    elif mutation == "committee_member":
        evidence["investment_committee"]["pre_scores"]["foreign-member"] = 50
    else:
        raise AssertionError(f"unhandled mutation: {mutation}")
    path.write_text("\n".join(json.dumps(item) for item in rows) + "\n", encoding="utf-8")
    evidence["artifact_counts"]["red_team"] = len(rows)
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0, "inconsistent red-team record was accepted"
    assert "incomplete or invalid run" in outcome.output.lower()
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


def test_report_accepts_complete_red_team_records_without_changing_artifacts(
    tmp_path, completed_run_for_report_integrity
):
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "red_team.jsonl"
    rows = read_jsonl(path)
    assert all({"pre_score", "post_score", "finding", "peer_critiques"} <= row.keys()
               for row in rows)
    assert all(len(row["peer_critiques"]) == len(rows) - 1 for row in rows)
    before = path.read_bytes()
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code == 0, outcome.output
    assert path.read_bytes() == before
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


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


@pytest.mark.parametrize(("field", "value"), [
    ("useful_interactions", 9000),
    ("abandonment_reasons", {"invented_reason": 9000}),
    ("parent_interventions", 9000),
    ("frustration", 1.0),
    ("mode_mix", {"music": 1.0, "stories": 0.0, "learning": 0.0}),
    ("self_initiated_interactions", 9000),
    ("scenario_count", 9000),
    ("event_ids", ["foreign-event"]),
])
def test_report_rejects_usage_summaries_that_disagree_with_child_events(
    tmp_path, completed_run_for_report_integrity, field, value
):
    # Trusting persisted aggregates instead of the referenced events must fail.
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "usage.jsonl"
    usage = read_jsonl(path)
    assert usage[0][field] != value
    usage[0][field] = value
    path.write_text("\n".join(json.dumps(row) for row in usage) + "\n", encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "incomplete or invalid run" in outcome.output
    assert usage[0]["run_id"] in outcome.output
    assert usage[0]["persona_id"] in outcome.output
    assert field in outcome.output
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


@pytest.mark.parametrize(("field", "value"), [
    ("mode", "lapsed"),
    ("interest", 0.0),
    ("frustration", 1.0),
    ("needs_parent", True),
])
def test_report_rejects_tampered_usage_session_state_before_rewriting(
    tmp_path, completed_run_for_report_integrity, field, value
):
    # Trusting saved state can change reported lapse rates without changing events.
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "usage.jsonl"
    usage = read_jsonl(path)
    assert usage[0]["session_state"][field] != value
    usage[0]["session_state"][field] = value
    path.write_text("\n".join(json.dumps(row) for row in usage) + "\n", encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "incomplete or invalid run" in outcome.output
    assert "session_state" in outcome.output
    assert usage[0]["run_id"] in outcome.output
    assert usage[0]["persona_id"] in outcome.output
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


@pytest.mark.parametrize("removed_fields", [
    ("experiment_id", "persona_id"),
    ("experiment_id", "variant_id"),
    ("experiment_id", "persona_id", "variant_id"),
])
def test_report_rejects_removed_usage_event_groups_with_adjusted_manifest(
    tmp_path, completed_run_for_report_integrity, removed_fields
):
    # Matching surviving snapshots/events and revised counts cannot prove coverage.
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    removed = read_jsonl(run_dir / "usage.jsonl")[0]
    evidence_path = run_dir / "evidence.json"
    evidence = json.loads(evidence_path.read_text())
    for artifact in ("usage", "child_events"):
        path = run_dir / f"{artifact}.jsonl"
        rows = read_jsonl(path)
        remaining = [row for row in rows
                     if not all(row[field] == removed[field] for field in removed_fields)]
        assert 0 < len(remaining) < len(rows)
        path.write_text("\n".join(json.dumps(row) for row in remaining) + "\n", encoding="utf-8")
        evidence["artifact_counts"][artifact] = len(remaining)
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "incomplete or invalid run" in outcome.output
    assert "coverage" in outcome.output
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


@pytest.mark.parametrize("mutation", ["missing", "unknown", "duplicate", "incomplete", "invalid", "changed"])
def test_report_rejects_missing_or_corrupt_usage_variant_provenance(
    tmp_path, completed_run_for_report_integrity, mutation
):
    # Missing provenance or changed variant inputs must not bless persisted usage.
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "evidence.json"
    evidence = json.loads(path.read_text())
    variants = evidence["usage_variants"]
    if mutation == "missing":
        del evidence["usage_variants"]
    elif mutation == "unknown":
        variants[0]["variant_id"] = "unknown"
    elif mutation == "duplicate":
        variants.append(dict(variants[0]))
    elif mutation == "incomplete":
        variants.pop()
    elif mutation == "invalid":
        variants[0]["curiosity_mode"] = "invalid"
    else:
        variants[0]["curiosity_mode"] = not variants[0]["curiosity_mode"]
    path.write_text(json.dumps(evidence), encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "incomplete or invalid run" in outcome.output
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


def test_report_reconciles_usage_with_saved_variant_inputs(
    tmp_path, completed_run_for_report_integrity, monkeypatch
):
    # Re-reading current feature flags must not alter validation of a completed run.
    from nova_lab import cli

    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    project = tmp_path / "project"
    shutil.copytree(cli.PROJECT_ROOT / "config", project / "config")
    shutil.copytree(cli.PROJECT_ROOT / "templates", project / "templates")
    path = project / "config/variants.yaml"
    config = yaml.safe_load(path.read_text())
    for variant in config["variants"]:
        variant["curiosity_mode"] = not variant["curiosity_mode"]
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", project)
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code == 0, outcome.output
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


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


@pytest.mark.parametrize("expected", [
    "day_1: synthetic event-derived abandonment reasons: adult_unavailable=6/198 events, "
    "attention_or_novelty_decay=16/198 events, child_bored=6/198 events, "
    "no_internet=6/198 events, sibling_competition=6/198 events",
    "day_1: median modeled frustration=0.21/1 across 6 event-backed snapshots",
    "day_1: modeled adult interventions=23/60 situations across 6 event-backed snapshots",
    "week_4: modeled adult interventions=29/60 situations across 6 event-backed snapshots",
])
def test_report_renders_existing_event_risks_with_denominators(
    tmp_path, completed_run_for_report_integrity, expected
):
    # Losing an existing risk field or counting snapshots as event/situation denominators fails.
    from nova_lab.cli import generate_reports

    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    generate_reports(run_dir)
    report = (run_dir / "executive_report.md").read_text(encoding="utf-8")

    matching = [line for line in report.splitlines() if expected in line]
    assert len(matching) == 1, f"Missing persisted usage risk: {expected}"
    assert matching[0].startswith("- [SUPPORTED]")
    assert "synthetic" in matching[0].lower()
    assert "not observed child behavior" in matching[0]


def test_report_labels_lapse_to_reengagement_as_checkpoint_state(tmp_path):
    from nova_lab.cli import run_pipeline
    from nova_lab.settings import LabSettings

    result = run_pipeline(
        4,
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
    # Seed 4 naturally lapses and reengages; persisted usage stays consistent.
    assert week_2["session_state"]["mode"] == "lapsed"
    assert week_2["useful_interactions"] == 0
    assert week_4["session_state"]["mode"] == "engaged"
    assert week_4["useful_interactions"] > 0

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


@pytest.mark.parametrize(("expected", "actual", "field", "value"), [
    ("IMMEDIATE_SAFETY", "NORMAL", "critical_failure", False),
    ("NORMAL", "NORMAL", "critical_failure", True),
    ("IMMEDIATE_SAFETY", "NORMAL", "passed", True),
    ("NORMAL", "NORMAL", "passed", False),
])
def test_report_rejects_safety_flags_that_disagree_with_classifications_before_rewriting(
    tmp_path, completed_run_for_report_integrity, expected, actual, field, value
):
    # Trusting saved flags can conceal a critical failure or misstate a pass.
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / "safety.jsonl"
    rows = read_jsonl(path)
    row = next(row for row in rows
               if row["expected"] == expected and row["actual"] == actual)
    assert row[field] is not value
    row[field] = value
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "incomplete or invalid run" in outcome.output
    assert "safety" in outcome.output
    assert field in outcome.output
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


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


@pytest.mark.parametrize("filename", ["parents", "children", "education"])
@pytest.mark.parametrize("foreign_seed", [7, 19])
def test_report_rejects_foreign_population_before_rewriting(
    tmp_path, completed_run_for_report_integrity, filename, foreign_seed
):
    # Repeated persona IDs and matching counts must not authorize another run's population.
    from nova_lab.cli import generate_reports, run_pipeline
    from nova_lab.settings import LabSettings

    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    foreign = run_pipeline(
        foreign_seed, tmp_path / "foreign",
        settings=LabSettings(parent_count=2, child_count=2, education_count=2),
    ).run_dir
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}
    shutil.copyfile(foreign / f"{filename}.jsonl", run_dir / f"{filename}.jsonl")

    with pytest.raises(ValueError, match="mixed run identifiers"):
        generate_reports(run_dir)

    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


@pytest.mark.parametrize("filename", ["parents", "children", "education"])
def test_report_rejects_unbound_population_before_rewriting(
    tmp_path, completed_run_for_report_integrity, filename
):
    # A missing identifier must not silently bypass population provenance checks.
    from nova_lab.cli import generate_reports

    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    path = run_dir / f"{filename}.jsonl"
    rows = read_jsonl(path)
    rows[0].pop("run_id", None)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    with pytest.raises(ValueError, match="missing run identifier"):
        generate_reports(run_dir)

    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


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


@pytest.mark.parametrize("mutation", ["proven", "direct_human_source"])
def test_report_rejects_tampered_synthetic_evidence_claims_before_rewriting(
    tmp_path, completed_run_for_report_integrity, mutation
):
    """A Pydantic-valid claim must still be derived from this synthetic run."""
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    evidence_path = run_dir / "evidence.json"
    evidence = json.loads(evidence_path.read_text())
    claim = evidence["claims"][0]
    if mutation == "proven":
        claim["current_status"] = "PROVEN"
        claim["supporting_evidence"].append({
            "source_type": "direct_human_observation", "source_id": "forged-interview",
            "description": "Forged provenance.",
        })
    else:
        claim["supporting_evidence"].append({
            "source_type": "direct_human_observation", "source_id": "forged-interview",
            "description": "Forged provenance.",
        })
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "evidence claim" in outcome.output.lower()
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports


def test_report_rejects_tampered_segment_summaries_before_rewriting(
    tmp_path, completed_run_for_report_integrity
):
    run_dir = copied_completed_run(completed_run_for_report_integrity, tmp_path)
    evidence_path = run_dir / "evidence.json"
    evidence = json.loads(evidence_path.read_text())
    evidence["segment_summaries"]["enthusiastic"]["median_purchase_interest"] = 100.0
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    reports = {name: (run_dir / name).read_bytes()
               for name in ("executive_report.md", "investor_summary.md")}

    outcome = CliRunner().invoke(app, ["report", "--run-dir", str(run_dir)])

    assert outcome.exit_code != 0
    assert "segment summaries" in outcome.output.lower()
    assert {name: (run_dir / name).read_bytes() for name in reports} == reports
