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

`nova-lab validate --config config/lab.yaml` loads the configuration and checks registry schemas, unique IDs, variant references, predeclared hypotheses/success criteria, supported families, and safety classes. Optional `--variants`, `--experiments`, and `--safety` paths select registries for validation; defaults are the repository registries used by `run`. Invalid input returns a nonzero exit code.

`nova-lab report --run-dir outputs/<run-id>` regenerates both Markdown reports from persisted artifacts without simulation. It rejects missing, empty, truncated, or schema-invalid required data, and checks every population row's `run_id` against `evidence.json`. Population-only runs and older runs without completion metadata or population run identifiers must be replaced by a new complete `run` before reports can be regenerated; matching persona IDs and counts do not establish provenance.

Each complete run writes:

```text
outputs/<run-id>/
  parents.jsonl
  children.jsonl
  education.jsonl
  red_team.jsonl
  observations.jsonl
  usage.jsonl
  child_events.jsonl
  safety.jsonl
  evidence.json
  executive_report.md
  investor_summary.md
```

The experiment registry covers variants A–F and positioning, pricing, privacy, learning, usage, and education families. `observations.jsonl` contains every experiment observation; `usage.jsonl` retains child/variant identity, session state, and the day 1, day 3, week 1, week 2, and week 4 checkpoints. `red_team.jsonl` includes persona details, critique findings, and committee pre/post scores. `evidence.json` includes evidence claims, parent segment summaries, focus-group scores, and committee scores. Reports retain evidence-status labels and the investor disclaimer.

`child_events.jsonl` records executed synthetic interaction sequences for every usage child/variant at all five checkpoints in ten situations: after school, bedtime, weekend, sibling competition, weak Wi-Fi, no internet, parent busy, child bored, sensitive question, and music only. Rows retain run, experiment, child, variant, situation, sequence, prompt/fixture response, before/after state, and evaluated outcome. Age and language ability affect question formulation; seeded transitions model clarification, misunderstanding, follow-up, lapse, and re-engagement. Sensitive questions bridge to an adult; offline knowledge requests refuse with an explicit reason. These are local fixtures, not tested product responses or observed child behavior.

The replaceable `ChildInteractionEngine` is injected through `run_pipeline(child_engine=...)`; its deterministic implementation requires no network or credentials. Usage snapshots reference their event IDs. The existing novelty-based useful-interaction estimate is multiplied by the executed useful-event count per situation (capped at 1); frustration, adult intervention, mode mix, self-initiation, and abandonment reasons come from events. Checkpoint engagement/lapse state remains the existing novelty model. Comprehension and transition rules are **uncalibrated design heuristics**, not learning or retention evidence. The report validates event schemas, run associations, session chains, counts, and usage links before rendering. Reports show persisted abandonment reasons per interaction event, median frustration across snapshots, and adult-help situations per scheduled situation at each checkpoint, all explicitly synthetic. Snapshot-only runs can still be reported when their completion metadata and population run identifiers are valid; they do not receive event-derived risk findings.

Parent evaluations receive neutral `concept-XX` identities and `Concept XX` labels in randomized order. Saved observations restore `variant_id` and retain `blinded_variant_id` for the mapping. Product descriptions and feature flags remain available for evaluation. Common deterministic noise depends only on seed, persona ID, and feature flags, so option, label, and run metadata changes do not create spurious paired effects.

The following **uncalibrated assumptions** drive comparisons; they are rules to stress-test, not measured preferences. Positioning assigns clarity scores of 50/65/70/55 to the four registry framings and explicit trust adjustments (AI enthusiasm helps the AI framing; skepticism penalizes it). Privacy design overrides the variant's default microphone assumptions: risk multipliers are 1/0.4/0.1, privacy-control bonuses 0/8/14 times privacy concern, and effort 0/8/14 times convenience orientation. Learning designs add 0/10/20 points times education orientation to child value, with effort 0/12/28 times convenience orientation. Effort reduces modeled purchase interest, so exploration can lose among convenience-oriented parents. Each observation discloses its applied assumptions. Evidence summaries keep paired metric deltas and unfavorable outcomes separately for each experiment ID; family reports aggregate all experiments in that family.

Pricing stores `offered_option` (device/monthly price) separately from `selected_option` (`buy_nova`, `competing_purchase`, or `defer`). The assumed commitment is device price plus three monthly payments. Competing family spending reserves 25% of the household budget when an existing device is owned, otherwise 10%; this is an explicit proxy rather than a measured alternative preference. Selection requires the commitment to fit the remaining budget, the monthly price to be no greater than `9.99 × subscription_tolerance`, and modeled interest of at least 50/100. Subscription price and intolerance also lower price fit and interest. Every offer is a separate hypothetical decision, not a cumulative shopping basket or real willingness to pay.

Safety output is an evaluator fixture exercise: expected-response fixtures and deliberately injected NORMAL-response negative controls. `critical_failure` remains explicit per case. No response classifier or real product answers are tested, so these checks do not establish product safety. Committee and focus-group score changes are explicit deterministic assumptions, not observed deliberation. Experiment summaries describe model output and do not automatically confirm the registry's hypotheses or success criteria.

Each red-team member first judges its role-specific proxy (for example, modeled trust for privacy or modeled price fit for finance), using its own rejection bias and a seed tied to persona and role. These initial judgments do not read peer scores. The subsequent committee step consumes the other eleven roles' evidence-gap critiques: severity is the peer's distance below 100, and the member's rejection bias weights the mean severity into a reduction of at most 12 points. `red_team.jsonl` retains every initial finding, pre/post score, and the contributing peer critiques with severity and adjustment. Role proxies and this deliberation rule are synthetic assumptions; no independent humans, LLMs, or real product evidence are implied.

Repeat the complete run with the same seed:

```bash
nova-lab run --config config/lab.yaml --provider deterministic
nova-lab run --config config/lab.yaml --provider deterministic
pytest tests/test_end_to_end.py -v
```

Each invocation creates a unique directory. The acceptance test compares all eleven artifacts across two runs, excluding only JSON `run_id` metadata; child events, observations, segment summaries, evidence statuses, and both reports must match exactly. Timestamps occur only in the unique run directory name and do not affect simulation results. Changing persona counts or registry definitions changes the experiment inputs.

## V1 release checkpoint — 2026-09-15

V1 requires **€0 and no paid provider**. The deterministic provider is the acceptance provider. Optional LLM adapters are not part of V1 acceptance; any future adapter needs separate evaluation and cost decisions.

The following checklist maps every acceptance criterion in design-spec section 14 to passing tests. Test paths are relative to `tests/`.

| Acceptance criterion | Passing test evidence |
| --- | --- |
| [x] Persona populations generated and schema-valid | `test_cli.py::test_generate_writes_schema_valid_populations_to_new_run_directory`; `test_end_to_end.py::test_v1_acceptance_run` validates all four default populations. |
| [x] Six product variants share common experiment definitions | `experiments/test_runner.py::test_runner_evaluates_one_parent_across_six_blinded_variants`; `experiments/test_registry.py::test_every_experiment_has_predeclared_hypothesis_and_success_criteria`. The default positioning definition compares A–F; other definitions select relevant subsets. |
| [x] At least five experiment families run reproducibly | `test_end_to_end.py::test_v1_acceptance_run` verifies persisted observations for six families; `test_end_to_end.py::test_fixed_seed_reproduces_all_semantic_artifacts_in_distinct_runs` compares all eleven artifacts. |
| [x] 30-day usage simulation covers all child segments | `test_end_to_end.py::test_v1_acceptance_run` verifies every one of 30 children, including ages 5–9, across B/C/E and all five checkpoints; `child/test_scenario_events.py` checks ten situations, executed interaction sequences, associations, propagation into usage/evidence/report, fixed-seed reproduction, and artifact integrity. `experiments/test_usage.py::test_high_curiosity_is_retained_while_low_curiosity_can_lapse_by_week_four` checks differing curiosity profiles. |
| [x] Red team preserves independent pre/post deliberation scores | `experiments/test_deliberation.py::test_red_team_initial_judgments_depend_on_role_and_not_panel_order` checks role-specific independent initial judgments; `experiments/test_deliberation.py::test_peer_critique_changes_post_scores_without_rewriting_initial_judgments` varies a real critique score and verifies its effect; `test_end_to_end.py::test_v1_acceptance_run` verifies disagreement, all 12 stored pre/post scores, and eleven contributing peer critiques per member. These remain deterministic synthetic judgments. |
| [x] Critical safety failures are separately flagged | `safety/test_safety.py::test_immediate_safety_answering_normal_is_critical_failure`; `safety/test_safety.py::test_refusal_answering_normal_is_critical_failure`; `test_end_to_end.py::test_v1_acceptance_run` checks persisted flags and visible negative controls. |
| [x] Evidence register is generated automatically | `test_end_to_end.py::test_v1_acceptance_run` verifies generated claims and segment summaries, with no synthetic claim marked PROVEN. |
| [x] Reports distinguish synthetic findings from real evidence | `reporting/test_reports.py::test_report_context_separates_proven_claims_from_synthetic_findings`; `reporting/test_reports.py::test_executive_report_labels_each_section_finding_with_its_evidence_status`; `reporting/test_reports.py::test_investor_report_contains_synthetic_disclaimer`. |
| [x] Rerun requires configuration only, not prompt reconstruction | `test_end_to_end.py::test_run_command_executes_pipeline_and_honors_population_settings`; `test_end_to_end.py::test_fixed_seed_reproduces_all_semantic_artifacts_in_distinct_runs`; `test_cli.py::test_validate_command_succeeds`. Use the commands above from the repository checkout. |

Release verification: the complete pytest suite and the installed `nova-lab validate` command must pass. Scan generated runs before cleanup with `rg -n -i 'product-market fit is proven|proven demand|will generate|guaranteed revenue' outputs/`; no matches is the expected result. Generated runs and Python caches are ignored by Git and can be recreated from configuration.
