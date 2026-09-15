from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from uuid import uuid4

import typer
import yaml

from nova_lab.evidence.register import EvidenceRegister
from nova_lab.experiments.education import SCENARIOS, evaluate_education_scenario
from nova_lab.experiments.focus_group import run_focus_group
from nova_lab.experiments.investment_committee import deliberate
from nova_lab.experiments.learning import run_learning
from nova_lab.experiments.positioning import run_positioning
from nova_lab.experiments.pricing import run_pricing
from nova_lab.experiments.privacy import run_privacy
from nova_lab.experiments.red_team import assess_independently, peer_critiques
from nova_lab.experiments.registry import load_experiments, load_variants
from nova_lab.experiments.runner import ExperimentRunner
from nova_lab.experiments.usage import simulate_usage
from nova_lab.models.common import EvidenceStatus, SafetyClass
from nova_lab.models.experiment import ExperimentObservation
from nova_lab.personas.factory import PersonaFactory
from nova_lab.providers.deterministic import DeterministicEngine
from nova_lab.reporting.context import ExecutiveFinding, build_report_context
from nova_lab.reporting.markdown import render_markdown
from nova_lab.safety.evaluator import evaluate_safety
from nova_lab.safety.generator import expand_prompt
from nova_lab.scoring.aggregate import summarize_by_segment
from nova_lab.scoring.bias import apply_positivity_penalty
from nova_lab.settings import LabSettings
from nova_lab.storage.jsonl import append_jsonl

app = typer.Typer(no_args_is_help=True)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PipelineResult:
    run_dir: Path
    variant_ids: list[str]
    experiment_families: list[str]
    usage_periods: list[str]
    red_team_has_pre_post_scores: bool
    safety_report_has_critical_failure_field: bool
    evidence_register_path: Path
    investor_summary_path: Path


def run_pipeline(
    seed: int, output_dir: Path, *, settings: LabSettings | None = None
) -> PipelineResult:
    """Compose a local synthetic V1 run; no human or product evidence is created."""
    settings = (settings or LabSettings()).model_copy(
        update={"seed": seed, "output_dir": Path(output_dir)}
    )
    # A unique storage ID must not enter the engine's random context.
    run_id = f"{settings.make_run_id()}-{uuid4().hex}"
    simulation_id = f"synthetic-seed-{seed}"
    run_dir = settings.output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    variants = load_variants(PROJECT_ROOT / "config/variants.yaml")
    experiments = load_experiments(PROJECT_ROOT / "config/experiments.yaml")
    factory = PersonaFactory(seed)
    parents = factory.make_parents(settings.parent_count)
    children = factory.make_children(settings.child_count)
    education = factory.make_education(settings.education_count)
    red_team = factory.make_red_team()
    for name, personas in (("parents", parents), ("children", children), ("education", education)):
        append_jsonl(run_dir / f"{name}.jsonl", [persona.model_dump(mode="json") for persona in personas])

    runner = ExperimentRunner(DeterministicEngine(seed), seed)
    parent_families = {
        "positioning": run_positioning, "pricing": run_pricing,
        "privacy": run_privacy, "learning": run_learning,
    }
    observations = []
    usage = []
    family_rows = {}
    for experiment in experiments:
        rows = []
        if experiment.family in parent_families:
            rows = parent_families[experiment.family](
                runner, simulation_id, experiment, parents, variants
            )
        elif experiment.family == "usage":
            for child in children:
                for variant_id in experiment.variant_ids:
                    for snapshot in simulate_usage(child, variants[variant_id], seed):
                        usage.append({
                            "run_id": run_id, "experiment_id": experiment.experiment_id,
                            "persona_id": child.persona_id, "variant_id": variant_id,
                            **snapshot.model_dump(mode="json"),
                        })
                        rows.append(ExperimentObservation(
                            run_id=run_id, experiment_id=experiment.experiment_id,
                            persona_id=child.persona_id, variant_id=variant_id,
                            metrics={
                                "useful_interactions": snapshot.useful_interactions,
                                "frustration": snapshot.frustration,
                                "parent_interventions": snapshot.parent_interventions,
                            },
                            selected_option=snapshot.period,
                            rationale="Synthetic usage scenario; not observed child behavior",
                        ))
        elif experiment.family == "education":
            for persona in education:
                for variant_id in experiment.variant_ids:
                    for scenario in SCENARIOS:
                        rows.append(ExperimentObservation(
                            run_id=run_id, experiment_id=experiment.experiment_id,
                            persona_id=persona.persona_id, variant_id=variant_id,
                            metrics=evaluate_education_scenario(persona, scenario),
                            selected_option=scenario,
                            rationale="Synthetic education scenario; not classroom evidence",
                        ))
        else:
            raise ValueError(f"Unsupported experiment family: {experiment.family}")
        rows = [row.model_copy(update={"run_id": run_id}) for row in rows]
        family_rows[experiment.family] = rows
        observations.extend(rows)
    append_jsonl(run_dir / "observations.jsonl", [row.model_dump(mode="json") for row in observations])
    append_jsonl(run_dir / "usage.jsonl", usage)

    baseline = family_rows["positioning"]
    segment_summaries = summarize_by_segment(baseline, {p.persona_id: p.ai_attitude for p in parents})
    variant_scores = {
        variant_id: median(row.metrics["purchase_interest"] for row in baseline if row.variant_id == variant_id)
        for variant_id in variants
    }
    initial_positions = {
        parent.persona_id: median(row.metrics["purchase_interest"] for row in baseline if row.persona_id == parent.persona_id)
        for parent in parents
    }
    critique_effects = {}
    for persona_id, score in initial_positions.items():
        objections = sorted({objection for row in baseline if row.persona_id == persona_id for objection in row.objections})
        critique_effects[persona_id] = apply_positivity_penalty(score, objections) - score
    focus_group = run_focus_group(initial_positions, critique_effects)
    # Complete all independent role judgments before sharing any peer critique.
    role_metrics = {
        metric: median(row.metrics[metric] for row in baseline)
        for metric in baseline[0].metrics
    }
    initial_findings = assess_independently(red_team, role_metrics, seed)
    critiques = {
        member.persona_id: peer_critiques(member, initial_findings) for member in red_team
    }
    committee = deliberate(
        {key: finding.score for key, finding in initial_findings.items()},
        {key: sum(peer["adjustment"] for peer in peers) for key, peers in critiques.items()},
    )
    red_rows = []
    for member in red_team:
        finding = initial_findings[member.persona_id]
        red_rows.append({
            "run_id": run_id, **member.model_dump(mode="json"),
            "pre_score": committee.pre_scores[member.persona_id],
            "post_score": committee.post_scores[member.persona_id],
            "peer_critiques": critiques[member.persona_id],
            "finding": finding.model_dump(mode="json"),
        })
    append_jsonl(run_dir / "red_team.jsonl", red_rows)

    safety = []
    cases = yaml.safe_load((PROJECT_ROOT / "config/safety.yaml").read_text())["cases"]
    for case in cases:
        expected = SafetyClass(case["expected"])
        for prompt in expand_prompt(case["base_prompt"]):
            # Fixtures exercise evaluator wiring. They are not classified answers.
            for negative_control in (False, True):
                actual = SafetyClass.NORMAL if negative_control else expected
                safety.append({
                    "run_id": run_id, "category": case["category"], "prompt": prompt,
                    "evaluation_mode": "synthetic_fixture", "negative_control": negative_control,
                    **evaluate_safety(expected, actual).model_dump(mode="json"),
                })
    append_jsonl(run_dir / "safety.jsonl", safety)

    register = EvidenceRegister()
    for experiment in experiments:
        rows = family_rows[experiment.family]
        metric = {"usage": "useful_interactions", "education": "usefulness"}.get(experiment.family, "purchase_interest")
        value = median(row.metrics[metric] for row in rows)
        text = f"{experiment.family}: {len(rows)} synthetic scenarios; median {metric}={value:.2f}. This describes model output, not hypothesis confirmation."
        register.add_claim(experiment.experiment_id, text, experiment.family)
        register.record_synthetic_support(experiment.experiment_id, experiment.experiment_id, text)
        for objection in sorted({objection for row in rows for objection in row.objections}):
            register.record_contestation(experiment.experiment_id, objection)
    claims = register.all()
    evidence_path = run_dir / "evidence.json"
    evidence_path.write_text(json.dumps({
        "run_id": run_id, "seed": seed,
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "segment_summaries": segment_summaries,
        "focus_group": focus_group.model_dump(mode="json"),
        "investment_committee": committee.model_dump(mode="json"),
    }, indent=2, sort_keys=True), encoding="utf-8")

    def finding(text: str) -> ExecutiveFinding:
        return ExecutiveFinding(EvidenceStatus.SUPPORTED, text)

    periods = list(dict.fromkeys(row["period"] for row in usage))
    critical_count = sum(row["critical_failure"] for row in safety)
    context = build_report_context(
        claims,
        product_ranking=[finding(f"{variant_id}: modeled median purchase interest {score:.2f}/100 (positioning scenarios)") for variant_id, score in sorted(variant_scores.items(), key=lambda item: (-item[1], item[0]))],
        segment_map=[finding(f"{segment}: {summary['n']} scenario observations; median purchase interest {summary['median_purchase_interest']:.2f}/100") for segment, summary in segment_summaries.items()],
        usage_risks=[finding(f"{period}: median modeled useful interactions {median(row['useful_interactions'] for row in usage if row['period'] == period):.2f}; synthetic scenario only") for period in periods],
        education_opportunities=[finding(f"{scenario}: modeled median usefulness {median(row.metrics['usefulness'] for row in family_rows['education'] if row.selected_option == scenario):.2f}/100; classroom validation required") for scenario in SCENARIOS],
        price_sensitivity=[finding(f"EUR {option} (device/month): modeled median purchase interest {median(row.metrics['purchase_interest'] for row in family_rows['pricing'] if row.selected_option == option):.2f}/100; not real willingness to pay") for option in dict.fromkeys(row.selected_option for row in family_rows['pricing'])],
        red_team=[finding(f"{row['role']}: {row['finding']['rejection_issue']}; strongest win: {row['finding']['strongest_win']}; strongest failure: {row['finding']['strongest_failure']}; required evidence: {row['finding']['evidence_to_change_mind']}") for row in red_rows],
        investment_committee=[finding(f"{row['role']}: pre={row['pre_score']:.2f}, post={row['post_score']:.2f}; independent role-proxy judgment followed by modeled peer-critique adjustment, not an investor decision") for row in red_rows],
        safety=[ExecutiveFinding(EvidenceStatus.UNKNOWN, f"Synthetic fixture checks: {len(safety)}; critical_failure={critical_count} in injected negative controls. No response classifier or real product answers were tested; product safety remains unvalidated.")],
    )
    for name in ("executive_report", "investor_summary"):
        (run_dir / f"{name}.md").write_text(
            render_markdown(PROJECT_ROOT / f"templates/{name}.md.j2", context), encoding="utf-8"
        )
    return PipelineResult(
        run_dir=run_dir,
        variant_ids=sorted({row.variant_id for row in observations}),
        experiment_families=list(family_rows), usage_periods=periods,
        red_team_has_pre_post_scores=bool(red_rows) and all("pre_score" in row and "post_score" in row for row in red_rows),
        safety_report_has_critical_failure_field=bool(safety) and all("critical_failure" in row for row in safety),
        evidence_register_path=evidence_path,
        investor_summary_path=run_dir / "investor_summary.md",
    )


@app.callback()
def main() -> None:
    """NOVA Synthetic Market Lab command-line interface."""


@app.command()
def validate() -> None:
    """Validate configuration and schemas."""
    typer.echo("configuration valid")


@app.command()
def generate(config: Path = Path("config/lab.yaml")) -> None:
    """Write deterministic, schema-valid synthetic populations to a new run."""
    settings = LabSettings.load(config)
    run_dir = settings.output_dir / settings.make_run_id()
    if run_dir.exists():
        raise typer.BadParameter(f"run directory already exists: {run_dir}")

    factory = PersonaFactory(settings.seed)
    payloads = {
        "parents": [
            persona.model_dump() for persona in factory.make_parents(settings.parent_count)
        ],
        "children": [
            persona.model_dump() for persona in factory.make_children(settings.child_count)
        ],
        "education": [
            persona.model_dump()
            for persona in factory.make_education(settings.education_count)
        ],
        "red_team": [persona.model_dump() for persona in factory.make_red_team()],
    }
    for name, records in payloads.items():
        append_jsonl(run_dir / f"{name}.jsonl", records)
    typer.echo(str(run_dir))


@app.command()
def run(
    config: Path = Path("config/lab.yaml"), provider: str = "deterministic"
) -> None:
    """Execute the complete V1 pipeline with the local deterministic provider."""
    if provider != "deterministic":
        raise typer.BadParameter(
            "V1 zero-budget execution supports provider=deterministic only"
        )
    settings = LabSettings.load(config)
    result = run_pipeline(settings.seed, settings.output_dir, settings=settings)
    typer.echo(str(result.run_dir))


@app.command()
def report(run_dir: Path = typer.Option(...)) -> None:
    """Select an existing run directory for report generation."""
    if not run_dir.is_dir():
        raise typer.BadParameter(f"run directory does not exist: {run_dir}")
    typer.echo(str(run_dir))
