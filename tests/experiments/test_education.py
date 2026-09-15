from nova_lab.experiments.education import evaluate_education_scenario
from nova_lab.models.persona import EducationPersona


def test_data_protection_role_penalizes_high_privacy_risk_scenario():
    persona = EducationPersona(
        persona_id="e1",
        role="data_protection_officer",
        setup_time_tolerance_minutes=5,
        privacy_concern=1.0,
        device_management_burden=0.7,
        pedagogical_openness=0.5,
        procurement_complexity=0.8,
        classroom_noise_sensitivity=0.5,
    )

    result = evaluate_education_scenario(persona, "circle_time")

    assert result["privacy_procurement_fit"] < 60
