from pathlib import Path

from nova_lab.experiments.registry import load_experiments, load_variants


def test_all_six_variants_are_registered():
    variants = load_variants(Path("config/variants.yaml"))

    assert set(variants) == {"A", "B", "C", "D", "E", "F"}


def test_every_experiment_has_predeclared_hypothesis_and_success_criteria():
    experiments = load_experiments(Path("config/experiments.yaml"))

    assert len(experiments) >= 5
    assert all(experiment.hypothesis.strip() for experiment in experiments)
    assert all(experiment.success_criteria.strip() for experiment in experiments)
