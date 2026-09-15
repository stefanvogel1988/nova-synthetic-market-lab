from pathlib import Path

import yaml

from nova_lab.models.experiment import ExperimentDefinition
from nova_lab.models.product import ProductVariant


REQUIRED_EXPERIMENT_FAMILIES = frozenset({
    "positioning", "pricing", "privacy", "learning", "usage", "education",
})


def load_variants(path: Path) -> dict[str, ProductVariant]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    variants = [ProductVariant.model_validate(item) for item in data["variants"]]
    if len({variant.variant_id for variant in variants}) != len(variants):
        raise ValueError("duplicate variant_id")
    return {variant.variant_id: variant for variant in variants}


def load_experiments(path: Path) -> list[ExperimentDefinition]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    experiments = [ExperimentDefinition.model_validate(item) for item in data["experiments"]]
    if len({experiment.experiment_id for experiment in experiments}) != len(experiments):
        raise ValueError("duplicate experiment_id")
    return experiments


def validate_registry(variants: dict[str, ProductVariant], experiments: list[ExperimentDefinition]) -> None:
    """Check predeclared hypotheses and runnable registry references."""
    if not variants or not experiments:
        raise ValueError("variants and experiments must be nonempty")
    if len({experiment.experiment_id for experiment in experiments}) != len(experiments):
        raise ValueError("duplicate experiment_id")
    for variant in variants.values():
        for field in ("variant_id", "label", "description"):
            if not getattr(variant, field).strip():
                raise ValueError(f"variant {field} must be nonempty")
    for experiment in experiments:
        for field in ("experiment_id", "hypothesis", "success_criteria", "scenario"):
            if not getattr(experiment, field).strip():
                raise ValueError(f"{experiment.experiment_id}: {field} must be nonempty")
        if experiment.family not in {"positioning", "pricing", "privacy", "learning", "usage", "education"}:
            raise ValueError(f"unsupported experiment family: {experiment.family}")
        if not experiment.variant_ids or len(set(experiment.variant_ids)) != len(experiment.variant_ids):
            raise ValueError(f"{experiment.experiment_id}: variant_ids must be nonempty and unique")
        unknown = set(experiment.variant_ids) - variants.keys()
        if unknown:
            raise ValueError(f"{experiment.experiment_id}: unknown variant references {sorted(unknown)}")
    missing_families = REQUIRED_EXPERIMENT_FAMILIES - {experiment.family for experiment in experiments}
    if missing_families:
        raise ValueError(
            "missing required experiment families: " + ", ".join(sorted(missing_families))
        )
