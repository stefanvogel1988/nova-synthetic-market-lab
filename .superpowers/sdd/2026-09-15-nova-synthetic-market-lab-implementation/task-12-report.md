# Task 12 Report: Synthetic Deliberation Contracts

## Files

- `src/nova_lab/experiments/focus_group.py`
- `src/nova_lab/experiments/red_team.py`
- `src/nova_lab/experiments/investment_committee.py`
- `tests/experiments/test_deliberation.py`

## RED

Added real behavior tests for deterministic synthetic focus-group updates,
red-team rejection/counterevidence fields and bounded scoring, and
investment-committee pre/post peer-critique snapshots.

```bash
/Users/stefanvogel/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/experiments/test_deliberation.py -v
```

Initial output: collection failed with `ModuleNotFoundError: No module named
'nova_lab.experiments.focus_group'`, because the deliberation modules did not
exist.

## GREEN

- `run_focus_group` applies deterministic, bounded critique effects and retains
  the initial and final synthetic positions.
- `RedTeamFinding` requires the strongest win/failure, rejection issue,
  bounded score, and evidence that would change the synthetic evaluator's
  conclusion.
- `deliberate` preserves investment-committee synthetic scores before and after
  bounded peer-critique adjustments.
- Module documentation explicitly limits these outputs to simulations; they do
  not claim that real parents, investors, or participants behaved this way.

Focused output: `3 passed in 0.04s`.

Full-suite command:

```bash
/Users/stefanvogel/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -v
```

Full-suite output: `38 passed in 0.08s`.
