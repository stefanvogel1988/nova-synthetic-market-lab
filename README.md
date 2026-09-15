# NOVA Synthetic Market Lab

Zero-budget synthetic validation for NOVA.

Synthetic findings are directional. They do not prove product-market fit, real purchase intent, learning outcomes, or future revenue.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest -q
nova-lab validate
```

## Reproducible V1 run

Run from this repository with Python 3.12 or newer:

```bash
python -m pip install -e '.[dev]'
pytest -q
nova-lab generate --config config/lab.yaml
nova-lab run --config config/lab.yaml --provider deterministic
```

The deterministic provider is a zero-cost synthetic test harness. Its outputs are directional and must not be described as real customer demand. Execution requires no credentials, network access, or paid APIs; initial installation requires the listed Python dependencies to be available.

`generate` creates a population-only run. `run` generates its own populations and executes the complete pipeline, printing the new output directory. The default configuration uses seed `20260915`, 150 parents, 30 children, 20 education personas, and the fixed panel of all 12 red-team roles. The V1 red-team factory always includes all 12 roles, irrespective of `red_team_count`.

Each complete run writes:

```text
outputs/<run-id>/
  parents.jsonl
  children.jsonl
  education.jsonl
  red_team.jsonl
  observations.jsonl
  usage.jsonl
  safety.jsonl
  evidence.json
  executive_report.md
  investor_summary.md
```

The experiment registry covers variants A–F and positioning, pricing, privacy, learning, usage, and education families. `observations.jsonl` contains every experiment observation; `usage.jsonl` retains child/variant identity, session state, and the day 1, day 3, week 1, week 2, and week 4 checkpoints. `red_team.jsonl` includes persona details, critique findings, and committee pre/post scores. `evidence.json` includes evidence claims, parent segment summaries, focus-group scores, and committee scores. Reports retain evidence-status labels and the investor disclaimer.

Safety output is an evaluator fixture exercise: expected-response fixtures and deliberately injected NORMAL-response negative controls. `critical_failure` remains explicit per case. No response classifier or real product answers are tested, so these checks do not establish product safety. Committee and focus-group score changes are explicit deterministic assumptions, not observed deliberation. Experiment summaries describe model output and do not automatically confirm the registry's hypotheses or success criteria.

Repeat the complete run with the same seed:

```bash
nova-lab run --config config/lab.yaml --provider deterministic
nova-lab run --config config/lab.yaml --provider deterministic
pytest tests/test_end_to_end.py -v
```

Each invocation creates a unique directory. The acceptance test compares all ten artifacts across two runs, excluding only JSON `run_id` metadata; observations, segment summaries, evidence statuses, and both reports must match exactly. Timestamps occur only in the unique run directory name and do not affect simulation results. Changing persona counts or registry definitions changes the experiment inputs.

## V1 release checkpoint — 2026-09-15

V1 requires **€0 and no paid provider**. The deterministic provider is the acceptance provider. Optional LLM adapters are not part of V1 acceptance; any future adapter needs separate evaluation and cost decisions.

The following checklist maps every acceptance criterion in design-spec section 14 to passing tests. Test paths are relative to `tests/`.

| Acceptance criterion | Passing test evidence |
| --- | --- |
| [x] Persona populations generated and schema-valid | `test_cli.py::test_generate_writes_schema_valid_populations_to_new_run_directory`; `test_end_to_end.py::test_v1_acceptance_run` validates all four default populations. |
| [x] Six product variants share common experiment definitions | `experiments/test_runner.py::test_runner_evaluates_one_parent_across_six_blinded_variants`; `experiments/test_registry.py::test_every_experiment_has_predeclared_hypothesis_and_success_criteria`. The default positioning definition compares A–F; other definitions select relevant subsets. |
| [x] At least five experiment families run reproducibly | `test_end_to_end.py::test_v1_acceptance_run` verifies persisted observations for six families; `test_end_to_end.py::test_fixed_seed_reproduces_all_semantic_artifacts_in_distinct_runs` compares all ten artifacts. |
| [x] 30-day usage simulation covers all child segments | `test_end_to_end.py::test_v1_acceptance_run` verifies every one of 30 children, including ages 5–9, across B/C/E and all five checkpoints; `experiments/test_usage.py::test_high_curiosity_is_retained_while_low_curiosity_can_lapse_by_week_four` checks differing curiosity profiles. |
| [x] Red team preserves independent pre/post deliberation scores | `experiments/test_deliberation.py::test_investment_committee_preserves_pre_and_post_peer_critique_scores`; `test_end_to_end.py::test_v1_acceptance_run` verifies all 12 stored findings with both scores. Initial scores and critique adjustments are deterministic assumptions, not independent human or LLM judgments. |
| [x] Critical safety failures are separately flagged | `safety/test_safety.py::test_immediate_safety_answering_normal_is_critical_failure`; `safety/test_safety.py::test_refusal_answering_normal_is_critical_failure`; `test_end_to_end.py::test_v1_acceptance_run` checks persisted flags and visible negative controls. |
| [x] Evidence register is generated automatically | `test_end_to_end.py::test_v1_acceptance_run` verifies generated claims and segment summaries, with no synthetic claim marked PROVEN. |
| [x] Reports distinguish synthetic findings from real evidence | `reporting/test_reports.py::test_report_context_separates_proven_claims_from_synthetic_findings`; `reporting/test_reports.py::test_executive_report_labels_each_section_finding_with_its_evidence_status`; `reporting/test_reports.py::test_investor_report_contains_synthetic_disclaimer`. |
| [x] Rerun requires configuration only, not prompt reconstruction | `test_end_to_end.py::test_run_command_executes_pipeline_and_honors_population_settings`; `test_end_to_end.py::test_fixed_seed_reproduces_all_semantic_artifacts_in_distinct_runs`; `test_cli.py::test_validate_command_succeeds`. Use the commands above from the repository checkout. |

Release verification: the complete pytest suite and the installed `nova-lab validate` command must pass. Scan generated runs before cleanup with `rg -n -i 'product-market fit is proven|proven demand|will generate|guaranteed revenue' outputs/`; no matches is the expected result. Generated runs and Python caches are ignored by Git and can be recreated from configuration.
