from nova_lab.models.persona import ParentPersona


def validate_parent_population(parents: list[ParentPersona]) -> list[str]:
    failures: list[str] = []
    if len({parent.ai_attitude for parent in parents}) < 4:
        failures.append("missing AI-attitude diversity")
    if not any(parent.ai_attitude == "opposed" for parent in parents):
        failures.append("missing rejecting parent segment")
    if not any(parent.privacy_concern >= 0.8 for parent in parents):
        failures.append("missing high-privacy segment")
    if not all(parent.disposable_budget_eur >= 0 for parent in parents):
        failures.append("negative household budget")
    return failures


def validate_population(parents: list[ParentPersona]) -> list[str]:
    return validate_parent_population(parents)
