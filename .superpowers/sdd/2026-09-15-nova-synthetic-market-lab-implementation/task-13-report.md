# Task 13 Report: Evidence Register and Decision Framework

## Files

- `src/nova_lab/evidence/register.py`
- `src/nova_lab/evidence/decision.py`
- `tests/evidence/test_register.py`

## RED

Added behavior tests for the synthetic-evidence ceiling, typed provenance from
experiment observations, and preservation of counterevidence in a contested
claim. The initial focused test run failed at collection because
`nova_lab.evidence` did not exist.

```bash
/Users/stefanvogel/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/evidence/test_register.py -v
```

## GREEN

- Synthetic evidence is stored as typed `EvidenceSource` records with
  `SYNTHETIC_EXPERIMENT` provenance.
- Synthetic support transitions claims to `SUPPORTED`, never `PROVEN`, and
  continues to require human validation.
- Experiment observations add support and retain stated objections as
  counterevidence; contested claims remain contested when later synthetic
  support arrives.
- The decision framework modifies contested claims and routes assumptions,
  unknowns, and supported claims to human validation.

Focused output: `3 passed in 0.05s`.

Full-suite command:

```bash
/Users/stefanvogel/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Full-suite output: `41 passed in 0.07s`.
