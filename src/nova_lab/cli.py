from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from uuid import uuid4

import typer
import yaml

from nova_lab.child.events import (
    ChildInteractionEngine, ChildInteractionEvent, DeterministicChildEngine,
)
from nova_lab.evidence.register import EvidenceRegister
from nova_lab.experiments.education import SCENARIOS, evaluate_education_scenario
from nova_lab.experiments.focus_group import run_focus_group
from nova_lab.experiments.investment_committee import deliberate
from nova_lab.experiments.learning import run_learning
from nova_lab.experiments.positioning import run_positioning
from nova_lab.experiments.pricing import run_pricing
from nova_lab.experiments.privacy import run_privacy
from nova_lab.experiments.red_team import assess_independently, peer_critiques, validate_red_team_records
from nova_lab.experiments.registry import load_experiments, load_variants, validate_registry
from nova_lab.experiments.runner import ExperimentRunner
from nova_lab.experiments.usage import UsageSnapshot, simulate_usage, validate_usage_events
from nova_lab.experiments.validation import validate_observations
from nova_lab.models.common import EvidenceStatus, SafetyClass
from nova_lab.models.experiment import ExperimentDefinition, ExperimentObservation
from nova_lab.models.evidence import EvidenceClaim
from nova_lab.models.persona import ParentPersona, ChildPersona, EducationPersona, RedTeamPersona
from nova_lab.models.product import ProductVariant
from nova_lab.personas.factory import PersonaFactory
from nova_lab.providers.base import JudgeEngine
from nova_lab.providers.deterministic import DeterministicEngine
from nova_lab.providers.judge import RubricJudge, reconcile_parent_product_score
from nova_lab.reporting.context import ExecutiveFinding, build_report_context
from nova_lab.reporting.markdown import render_markdown
from nova_lab.safety.evaluator import SafetyResult, evaluate_safety
from nova_lab.safety.generator import expand_prompt
from nova_lab.scoring.aggregate import summarize_by_segment
from nova_lab.scoring.bias import apply_positivity_penalty, detect_preference_decision_contradiction
from nova_lab.settings import LabSettings
from nova_lab.storage.jsonl import append_jsonl, read_jsonl

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
    seed: int, output_dir: Path, *, settings: LabSettings | None = None,
    judge: JudgeEngine | None = None,
    child_engine: ChildInteractionEngine | None = None,
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
    validate_registry(variants, experiments)
    factory = PersonaFactory(seed)
    parents = factory.make_parents(settings.parent_count)
    children = factory.make_children(settings.child_count)
    education = factory.make_education(settings.education_count)
    red_team = factory.make_red_team()
    for name, personas in (("parents", parents), ("children", children), ("education", education)):
        append_jsonl(run_dir / f"{name}.jsonl", [
            {"run_id": run_id, **persona.model_dump(mode="json")} for persona in personas
        ])

    runner = ExperimentRunner(DeterministicEngine(seed), seed)
    judge = judge if judge is not None else RubricJudge()
    child_engine = child_engine if child_engine is not None else DeterministicChildEngine()
    parent_families = {
        "positioning": run_positioning, "pricing": run_pricing,
        "privacy": run_privacy, "learning": run_learning,
    }
    observations = []
    usage = []
    child_events = []
    family_rows = {}
    experiment_rows = {}
    for experiment in experiments:
        rows = []
        if experiment.family in parent_families:
            rows = parent_families[experiment.family](
                runner, simulation_id, experiment, parents, variants
            )
        elif experiment.family == "usage":
            for child in children:
                for variant_id in experiment.variant_ids:
                    events = child_engine.simulate(
                        child, variants[variant_id], seed,
                        run_id=run_id, experiment_id=experiment.experiment_id,
                    )
                    child_events.extend(events)
                    for snapshot in simulate_usage(child, variants[variant_id], seed, events=events):
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
                                "self_initiated_interactions": snapshot.self_initiated_interactions,
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
        if experiment.family in parent_families:
            judged_rows = []
            for row in rows:
                # Pricing has now finalized an explicit choice. Scenario labels
                # in other families are not purchase rejections.
                if "selected_nova" in row.metrics and detect_preference_decision_contradiction(
                    row.metrics["purchase_interest"], bool(row.metrics["selected_nova"])
                ):
                    row = row.model_copy(update={"objections": sorted({
                        *row.objections, "preference_decision_contradiction",
                    })})
                judged_rows.append(row.model_copy(update={
                    "metrics": {**row.metrics, **judge.score(row)},
                }))
            rows = judged_rows
        experiment_rows[experiment.experiment_id] = rows
        family_rows.setdefault(experiment.family, []).extend(rows)
        observations.extend(rows)
    append_jsonl(run_dir / "observations.jsonl", [row.model_dump(mode="json") for row in observations])
    append_jsonl(run_dir / "usage.jsonl", usage)
    append_jsonl(run_dir / "child_events.jsonl", [event.model_dump(mode="json") for event in child_events])

    baseline = family_rows["positioning"]
    segment_summaries = summarize_by_segment(baseline, {p.persona_id: p.ai_attitude for p in parents})
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

    claims = build_evidence_claims(experiments, experiment_rows)
    evidence_path = run_dir / "evidence.json"
    evidence_path.write_text(json.dumps({
        "run_id": run_id, "seed": seed,
        "experiments": [experiment.model_dump(mode="json") for experiment in experiments],
        "usage_variants": [variants[variant_id].model_dump(mode="json") for variant_id in sorted({
            variant_id for experiment in experiments if experiment.family == "usage"
            for variant_id in experiment.variant_ids
        })],
        "artifact_counts": {
            "parents": len(parents), "children": len(children), "education": len(education),
            "observations": len(observations), "usage": len(usage), "red_team": len(red_rows),
            "safety": len(safety),
            "child_events": len(child_events),
        },
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "segment_summaries": segment_summaries,
        "focus_group": focus_group.model_dump(mode="json"),
        "investment_committee": committee.model_dump(mode="json"),
    }, indent=2, sort_keys=True), encoding="utf-8")

    generate_reports(run_dir)
    periods = list(dict.fromkeys(row["period"] for row in usage))
    return PipelineResult(
        run_dir=run_dir,
        variant_ids=sorted({row.variant_id for row in observations}),
        experiment_families=list(family_rows), usage_periods=periods,
        red_team_has_pre_post_scores=bool(red_rows) and all("pre_score" in row and "post_score" in row for row in red_rows),
        safety_report_has_critical_failure_field=bool(safety) and all("critical_failure" in row for row in safety),
        evidence_register_path=evidence_path,
        investor_summary_path=run_dir / "investor_summary.md",
    )


def paired_comparisons(family: str, rows: list[ExperimentObservation]) -> str:
    """Describe within-persona/variant deltas without treating assumptions as proof."""
    metrics = {
        "positioning": ("product_clarity", "trust", "purchase_interest"),
        "privacy": ("trust", "operational_friction", "purchase_interest"),
        "learning": ("child_value", "operational_friction", "purchase_interest"),
    }.get(family)
    if not metrics:
        return ""
    options = list(dict.fromkeys(row.selected_option for row in rows))
    baseline = { (row.persona_id, row.variant_id): row for row in rows if row.selected_option == options[0] }
    summaries = []
    for option in options[1:]:
        pairs = [(baseline[(row.persona_id, row.variant_id)], row) for row in rows if row.selected_option == option]
        deltas = ", ".join(f"median delta {metric}={median(b.metrics[metric] - a.metrics[metric] for a, b in pairs):+.2f}" for metric in metrics)
        unfavorable = sum(b.metrics["purchase_interest"] < a.metrics["purchase_interest"] for a, b in pairs)
        summaries.append(f"{option} vs {options[0]}: {len(pairs)} paired comparisons, {deltas}; unfavorable purchase-interest outcomes={unfavorable}/{len(pairs)}")
    return " ASSUMPTION-driven paired comparisons: " + "; ".join(summaries) + ". Uncalibrated rules; human validation required."


def _canonical_evidence_rows(rows: list[ExperimentObservation]) -> list[ExperimentObservation]:
    """Give persisted-order-independent evidence claims a reproducible input order."""
    return sorted(rows, key=lambda row: (
        row.persona_id, row.variant_id, row.selected_option or "", row.offered_option or "",
        json.dumps(row.metrics, sort_keys=True), row.rationale,
    ))


def build_evidence_claims(
    experiments: list[ExperimentDefinition], experiment_rows: dict[str, list[ExperimentObservation]],
) -> list[EvidenceClaim]:
    """Derive the only evidence claims allowed for a completed synthetic run."""
    register = EvidenceRegister()
    for experiment in experiments:
        rows = _canonical_evidence_rows(experiment_rows[experiment.experiment_id])
        metric = {"usage": "useful_interactions", "education": "usefulness"}.get(
            experiment.family, "purchase_interest"
        )
        value = median(row.metrics[metric] for row in rows)
        text = (
            f"{experiment.family}: {len(rows)} synthetic scenarios; median {metric}={value:.2f}. "
            "This describes model output, not hypothesis confirmation."
        )
        text += paired_comparisons(experiment.family, rows)
        register.add_claim(experiment.experiment_id, text, experiment.family)
        register.record_synthetic_support(experiment.experiment_id, experiment.experiment_id, text)
        for objection in sorted({objection for row in rows for objection in row.objections}):
            register.record_contestation(experiment.experiment_id, objection)
    return register.all()


def _validate_persisted_population(payloads: dict[str, list[dict]], seed: int) -> None:
    """Bind population artifacts to the deterministic population that produced a run."""
    factory = PersonaFactory(seed)
    expected = {
        "parents": factory.make_parents(len(payloads["parents"])),
        "children": factory.make_children(len(payloads["children"])),
        "education": factory.make_education(len(payloads["education"])),
    }
    models = {
        "parents": ParentPersona,
        "children": ChildPersona,
        "education": EducationPersona,
    }
    for name, personas in expected.items():
        actual = [models[name].model_validate(row) for row in payloads[name]]
        if sorted(actual, key=lambda persona: persona.persona_id) != personas:
            raise ValueError(f"{name} population differs from the deterministic run population")


def _expected_safety_fixtures() -> list[dict]:
    cases = yaml.safe_load((PROJECT_ROOT / "config/safety.yaml").read_text(encoding="utf-8"))["cases"]
    fixtures = []
    for case in cases:
        expected = SafetyClass(case["expected"])
        for prompt in expand_prompt(case["base_prompt"]):
            for negative_control in (False, True):
                actual = SafetyClass.NORMAL if negative_control else expected
                fixtures.append({
                    "category": case["category"], "prompt": prompt,
                    "evaluation_mode": "synthetic_fixture", "negative_control": negative_control,
                    **evaluate_safety(expected, actual).model_dump(mode="json"),
                })
    return fixtures


def _validate_safety_fixtures(rows: list[dict]) -> None:
    fields = (
        "category", "prompt", "evaluation_mode", "negative_control", "expected", "actual",
        "critical_failure", "passed",
    )
    actual = sorted(
        (json.dumps({field: row.get(field) for field in fields}, sort_keys=True) for row in rows)
    )
    expected = sorted(json.dumps(row, sort_keys=True) for row in _expected_safety_fixtures())
    if actual != expected:
        raise ValueError("safety fixtures differ from configured injected controls")


def generate_reports(run_dir: Path) -> None:
    """Rebuild reports from a complete persisted run without rerunning simulations."""
    try:
        evidence = json.loads((run_dir / "evidence.json").read_text(encoding="utf-8"))
        payloads = {name: read_jsonl(run_dir / f"{name}.jsonl") for name in (
            "parents", "children", "education", "observations", "usage", "red_team", "safety",
        )}
        if "child_events" in evidence["artifact_counts"]:
            payloads["child_events"] = read_jsonl(run_dir / "child_events.jsonl")
        elif any(row.get("event_ids") for row in payloads["usage"]):
            raise ValueError("missing child event completion metadata")
        if not all(payloads.values()) or not evidence["claims"] or not evidence["experiments"]:
            raise ValueError("empty required artifacts")
        if {name: len(rows) for name, rows in payloads.items()} != evidence["artifact_counts"]:
            raise ValueError("artifact counts do not match the completed run")
        for name, model in (("parents", ParentPersona), ("children", ChildPersona),
                            ("education", EducationPersona), ("red_team", RedTeamPersona),
                            ("usage", UsageSnapshot)):
            for row in payloads[name]:
                model.model_validate(row)
        for row in payloads["safety"]:
            result = SafetyResult.model_validate(row)
            reconciled = evaluate_safety(result.expected, result.actual)
            for field in ("passed", "critical_failure"):
                if getattr(result, field) != getattr(reconciled, field):
                    raise ValueError(f"safety {field} disagrees with expected/actual classifications")
        evidence_run_id = evidence.get("run_id")
        if not isinstance(evidence_run_id, str) or not evidence_run_id.strip():
            raise ValueError("missing evidence run identifier")
        for name in ("parents", "children", "education", "usage", "red_team", "safety",
                     *(["child_events"] if "child_events" in payloads else [])):
            for row in payloads[name]:
                artifact_run_id = row.get("run_id")
                if not isinstance(artifact_run_id, str) or not artifact_run_id.strip():
                    raise ValueError(f"missing run identifier in {name} artifact")
                if artifact_run_id != evidence_run_id:
                    raise ValueError("mixed run identifiers")
        _validate_persisted_population(payloads, evidence["seed"])
        _validate_safety_fixtures(payloads["safety"])
        observations = [ExperimentObservation.model_validate(row) for row in payloads["observations"]]
        experiments = [ExperimentDefinition.model_validate(row) for row in evidence["experiments"]]
        validate_observations(
            observations, run_id=evidence_run_id, experiments=experiments,
            variants=load_variants(PROJECT_ROOT / "config/variants.yaml"),
            parents=[ParentPersona.model_validate(row) for row in payloads["parents"]],
            children=[ChildPersona.model_validate(row) for row in payloads["children"]],
            education=[EducationPersona.model_validate(row) for row in payloads["education"]],
        )
        if "child_events" in payloads:
            validate_usage_events(
                [ChildInteractionEvent.model_validate(row) for row in payloads["child_events"]],
                payloads["usage"], [ChildPersona.model_validate(row) for row in payloads["children"]],
                [ProductVariant.model_validate(row) for row in evidence["usage_variants"]],
                {e.experiment_id: e.variant_ids for e in experiments if e.family == "usage"},
                evidence["seed"],
            )
        claims = [EvidenceClaim.model_validate(row) for row in evidence["claims"]]
        family_by_id = {experiment.experiment_id: experiment.family for experiment in experiments}
        family_rows = {}
        for row in observations:
            if family_by_id[row.experiment_id] in {"positioning", "pricing", "privacy", "learning"}:
                row.metrics["parent_product_score"] = reconcile_parent_product_score(row)
            family_rows.setdefault(family_by_id[row.experiment_id], []).append(row)
        if not {"positioning", "pricing", "education", "usage"} <= family_rows.keys():
            raise ValueError("missing report families")
        baseline = family_rows["positioning"]
        red_team_members = PersonaFactory(evidence["seed"]).make_red_team()
        role_metrics = {
            metric: median(row.metrics[metric] for row in baseline)
            for metric in baseline[0].metrics
        }
        validate_red_team_records(
            payloads["red_team"], run_id=evidence_run_id, members=red_team_members,
            committee=evidence["investment_committee"],
            expected_findings=assess_independently(red_team_members, role_metrics, evidence["seed"]),
        )
        expected_claims = build_evidence_claims(experiments, {
            experiment.experiment_id: [
                row for row in observations if row.experiment_id == experiment.experiment_id
            ]
            for experiment in experiments
        })
        if [claim.model_dump(mode="json") for claim in claims] != [
            claim.model_dump(mode="json") for claim in expected_claims
        ]:
            raise ValueError("evidence claims disagree with validated observations")
        expected_segment_summaries = summarize_by_segment(
            baseline,
            {
                parent.persona_id: parent.ai_attitude
                for parent in (ParentPersona.model_validate(row) for row in payloads["parents"])
            },
        )
        segment_summaries = evidence["segment_summaries"]
        if segment_summaries != expected_segment_summaries:
            raise ValueError("segment summaries disagree with validated positioning observations")
        variant_scores = {variant_id: median(
            row.metrics["parent_product_score"]
            for row in baseline if row.variant_id == variant_id)
            for variant_id in sorted({row.variant_id for row in baseline})}
        usage, red_rows, safety = payloads["usage"], payloads["red_team"], payloads["safety"]
        context = report_context(claims, family_rows, variant_scores, segment_summaries, usage, red_rows, safety)
        rendered = {name: render_markdown(PROJECT_ROOT / f"templates/{name}.md.j2", context)
            for name in ("executive_report", "investor_summary")}
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"incomplete or invalid run: {error}") from error
    for name, content in rendered.items():
        (run_dir / f"{name}.md").write_text(content, encoding="utf-8")


def report_context(claims, family_rows, variant_scores, segment_summaries, usage, red_rows, safety):
    def finding(text: str) -> ExecutiveFinding:
        return ExecutiveFinding(EvidenceStatus.SUPPORTED, text)

    periods = list(dict.fromkeys(row["period"] for row in usage))
    event_risks = []
    for period in periods:
        rows = [row for row in usage if row["period"] == period and row.get("event_ids")]
        if not rows:
            continue
        event_count = sum(len(row["event_ids"]) for row in rows)
        situation_count = sum(row["scenario_count"] for row in rows)
        reasons = Counter()
        for row in rows:
            reasons.update(row.get("abandonment_reasons", {}))
        reason_counts = ", ".join(
            f"{reason}={count}/{event_count} events" for reason, count in sorted(reasons.items())
        ) or f"none recorded=0/{event_count} events"
        event_risks.extend([
            finding(
                f"{period}: synthetic event-derived abandonment reasons: {reason_counts}. "
                "Denominator: all child interaction events at this checkpoint; "
                "counts are not unique children or situations; not observed child behavior."
            ),
            finding(
                f"{period}: median modeled frustration={median(row['frustration'] for row in rows):.2f}/1 "
                f"across {len(rows)} event-backed snapshots; each snapshot stores mean final-state "
                "frustration across its situations; synthetic only, not observed child behavior."
            ),
            finding(
                f"{period}: modeled adult interventions={sum(row['parent_interventions'] for row in rows):g}/"
                f"{situation_count} situations across {len(rows)} event-backed snapshots; "
                "counts situations with explicit adult help, not unique adults or children; "
                "synthetic only, not observed child behavior."
            ),
        ])
    critical_fixtures = [
        row for row in safety if row["negative_control"] and row["critical_failure"]
    ]
    critical_count = len(critical_fixtures)
    education_rows = family_rows["education"]
    education_fit = sum(
        row.metrics["usefulness"] >= 65
        and row.metrics["administration_burden"] <= 40
        for row in education_rows
    )
    usefulness_blockers = sum(
        row.metrics["usefulness"] < 65 for row in education_rows
    )
    burden_blockers = sum(
        row.metrics["administration_burden"] > 40 for row in education_rows
    )
    privacy_fits = [row.metrics["privacy_procurement_fit"] for row in education_rows]
    critical_categories = [
        f"{category}={sum(row['critical_failure'] for row in rows)}/{len(rows)}"
        for category in sorted({row["category"] for row in critical_fixtures})
        for rows in [[row for row in safety if row["category"] == category]]
    ]
    return build_report_context(
        claims,
        product_ranking=[finding(f"{variant_id}: modeled median judged parent/product score {score:.2f}/100 (positioning scenarios; synthetic rubric judgment, not demand)") for variant_id, score in sorted(variant_scores.items(), key=lambda item: (-item[1], item[0]))],
        segment_map=[finding(f"{segment}: {summary['n']} scenario observations; median purchase interest {summary['median_purchase_interest']:.2f}/100") for segment, summary in segment_summaries.items()],
        usage_risks=[
            *([
                finding(
                    f"Executed synthetic child interaction events: {sum(len(row.get('event_ids', [])) for row in usage)}; "
                    f"{max(row.get('scenario_count', 0) for row in usage)} usage situations at each checkpoint. "
                    "Comprehension and event outcomes are uncalibrated design heuristics, not observed child behavior."
                ),
            ] if any(row.get("event_ids") for row in usage) else []),
            *event_risks,
            *[
                finding(
                    f"{period}: engaged at checkpoint sessions="
                    f"{sum(row['session_state']['mode'] == 'engaged' for row in rows)}/{len(rows)}; "
                    f"lapsed sessions={sum(row['session_state']['mode'] == 'lapsed' for row in rows)}/{len(rows)}; "
                    f"median modeled useful interactions={median(row['useful_interactions'] for row in rows):.2f}; "
                    "synthetic scenario only"
                )
                for period in periods
                for rows in [[row for row in usage if row["period"] == period]]
            ],
            finding(
                "Negative usage signal distribution across 30-day snapshots: "
                f"lapsed={sum(row['session_state']['mode'] == 'lapsed' for row in usage)}/{len(usage)}; "
                f"zero-use={sum(row['useful_interactions'] == 0 for row in usage)}/{len(usage)}. "
                "These are modeled session states, not observed child retention."
            ),
        ],
        education_opportunities=[
            finding(
                f"Modeled education adoption/fit: {education_fit}/{len(education_rows)} "
                "scenario-persona results meet the configured usefulness and administration thresholds; "
                "this is a synthetic fit screen, not adoption evidence."
            ),
            finding(
                f"Modeled education rejection/blocking: {len(education_rows) - education_fit}/{len(education_rows)} "
                "scenario-persona results fail at least one configured fit threshold; "
                "this is not observed institutional rejection."
            ),
            finding(
                f"Central modeled blockers: usefulness below 65/100={usefulness_blockers}/{len(education_rows)}; "
                f"administration burden above 40/100={burden_blockers}/{len(education_rows)}. "
                f"Privacy/procurement fit distribution: min={min(privacy_fits):.2f}/100, "
                f"median={median(privacy_fits):.2f}/100, max={max(privacy_fits):.2f}/100; "
                "classroom validation required."
            ),
            *[
                finding(f"{scenario}: modeled median usefulness {median(row.metrics['usefulness'] for row in education_rows if row.selected_option == scenario):.2f}/100; classroom validation required")
                for scenario in SCENARIOS
            ],
        ],
        price_sensitivity=[finding(f"EUR {option} (device/month): modeled median purchase interest {median(row.metrics['purchase_interest'] for row in family_rows['pricing'] if row.offered_option == option):.2f}/100; modeled NOVA selections={sum(row.selected_option == 'buy_nova' for row in family_rows['pricing'] if row.offered_option == option)}/{sum(row.offered_option == option for row in family_rows['pricing'])}; three-month commitment and competing budget enforced; not real willingness to pay") for option in dict.fromkeys(row.offered_option for row in family_rows['pricing'])],
        red_team=[finding(f"{row['role']}: {row['finding']['rejection_issue']}; strongest win: {row['finding']['strongest_win']}; strongest failure: {row['finding']['strongest_failure']}; required evidence: {row['finding']['evidence_to_change_mind']}") for row in red_rows],
        investment_committee=[finding(f"{row['role']}: pre={row['pre_score']:.2f}, post={row['post_score']:.2f}; independent role-proxy judgment followed by modeled peer-critique adjustment, not an investor decision") for row in red_rows],
        safety=[
            ExecutiveFinding(EvidenceStatus.UNKNOWN, f"Synthetic fixture checks: {len(safety)}; critical_failure={critical_count} in injected negative controls. No response classifier or real product answers were tested; product safety remains unvalidated."),
            ExecutiveFinding(EvidenceStatus.UNKNOWN, "Critical-risk fixture categories (injected negative controls): " + ", ".join(critical_categories) + ". These fixtures do not test product responses."),
        ],
    )


@app.callback()
def main() -> None:
    """NOVA Synthetic Market Lab command-line interface."""


@app.command()
def validate(
    config: Path = Path("config/lab.yaml"),
    variants: Path = PROJECT_ROOT / "config/variants.yaml",
    experiments: Path = PROJECT_ROOT / "config/experiments.yaml",
    safety: Path = PROJECT_ROOT / "config/safety.yaml",
) -> None:
    """Validate configuration and schemas."""
    try:
        LabSettings.load(config)
        validate_registry(load_variants(variants), load_experiments(experiments))
        cases = yaml.safe_load(safety.read_text(encoding="utf-8"))["cases"]
        if not cases:
            raise ValueError("safety cases must be nonempty")
        for case in cases:
            if not case["category"].strip() or not case["base_prompt"].strip():
                raise ValueError("safety category and base_prompt must be nonempty")
            if case["expected"] not in {value.value for value in SafetyClass}:
                raise ValueError(f"invalid safety expected class: {case['expected']}")
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        typer.echo(f"configuration invalid: {error}", err=True)
        raise typer.Exit(code=1) from error
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
    """Regenerate Markdown reports from complete persisted run artifacts."""
    if not run_dir.is_dir():
        raise typer.BadParameter(f"run directory does not exist: {run_dir}")
    try:
        generate_reports(run_dir)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(str(run_dir))
