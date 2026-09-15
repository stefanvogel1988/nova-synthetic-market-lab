from pydantic import BaseModel


class ExperimentDefinition(BaseModel):
    experiment_id: str
    family: str
    hypothesis: str
    success_criteria: str
    scenario: str
    variant_ids: list[str]


class ExperimentObservation(BaseModel):
    run_id: str
    experiment_id: str
    persona_id: str
    variant_id: str
    metrics: dict[str, float]
    objections: list[str] = []
    selected_option: str | None = None
    rationale: str = ""
