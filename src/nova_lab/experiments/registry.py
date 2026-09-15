from pathlib import Path

import yaml

from nova_lab.models.experiment import ExperimentDefinition
from nova_lab.models.product import ProductVariant


def load_variants(path: Path) -> dict[str, ProductVariant]:
    data = yaml.safe_load(path.read_text())
    variants = [ProductVariant.model_validate(item) for item in data["variants"]]
    return {variant.variant_id: variant for variant in variants}


def load_experiments(path: Path) -> list[ExperimentDefinition]:
    data = yaml.safe_load(path.read_text())
    return [ExperimentDefinition.model_validate(item) for item in data["experiments"]]
