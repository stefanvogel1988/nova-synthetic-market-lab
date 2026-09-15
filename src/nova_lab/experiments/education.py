"""Deterministic, synthetic-only evaluation of education scenarios."""

from nova_lab.models.persona import EducationPersona


SCENARIOS = [
    "free_learning_station",
    "circle_time",
    "theme_week",
    "reading_support",
    "classroom_music",
    "substitute_teacher",
    "fleet_management",
]


def evaluate_education_scenario(
    persona: EducationPersona, scenario: str
) -> dict[str, float]:
    """Return bounded synthetic scores for one education scenario.

    These scores are deterministic scenario estimates, not observed market or
    classroom evidence. Operational burden and privacy/procurement fit remain
    explicit so synthetic usefulness does not imply deployment readiness.
    """
    usefulness = 45 + persona.pedagogical_openness * 40
    burden = 25 + persona.device_management_burden * 50
    privacy_fit = 80 - persona.privacy_concern * 35 - persona.procurement_complexity * 20

    if scenario == "fleet_management":
        burden += 15
    if persona.role == "data_protection_officer":
        privacy_fit -= 15

    return {
        "usefulness": round(max(0, min(100, usefulness)), 2),
        "administration_burden": round(max(0, min(100, burden)), 2),
        "privacy_procurement_fit": round(max(0, min(100, privacy_fit)), 2),
    }
