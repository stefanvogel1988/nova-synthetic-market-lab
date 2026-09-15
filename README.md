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
