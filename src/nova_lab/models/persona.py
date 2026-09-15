from pydantic import BaseModel, Field


class ParentPersona(BaseModel):
    persona_id: str
    child_age: int = Field(ge=5, le=9)
    child_count: int = Field(ge=1, le=6)
    disposable_budget_eur: float = Field(ge=0)
    price_sensitivity: float = Field(ge=0, le=1)
    ai_attitude: str
    privacy_concern: float = Field(ge=0, le=1)
    subscription_tolerance: float = Field(ge=0, le=1)
    existing_devices: list[str]
    streaming_service: str
    technical_confidence: float = Field(ge=0, le=1)
    education_orientation: float = Field(ge=0, le=1)
    convenience_orientation: float = Field(ge=0, le=1)
    screen_time_philosophy: str
    locale_type: str


class ChildPersona(BaseModel):
    persona_id: str
    age: int = Field(ge=5, le=9)
    curiosity_frequency: float = Field(ge=0, le=1)
    language_ability: float = Field(ge=0, le=1)
    reading_ability: float = Field(ge=0, le=1)
    attention_span: float = Field(ge=0, le=1)
    willingness_to_speak_to_devices: float = Field(ge=0, le=1)
    frustration_tolerance: float = Field(ge=0, le=1)
    novelty_seeking: float = Field(ge=0, le=1)
    sibling_context: str
    preference_music: float = Field(ge=0, le=1)
    preference_stories: float = Field(ge=0, le=1)
    preference_learning: float = Field(ge=0, le=1)
    preferred_domains: list[str]


class EducationPersona(BaseModel):
    persona_id: str
    role: str
    setup_time_tolerance_minutes: int = Field(ge=0)
    privacy_concern: float = Field(ge=0, le=1)
    device_management_burden: float = Field(ge=0, le=1)
    pedagogical_openness: float = Field(ge=0, le=1)
    procurement_complexity: float = Field(ge=0, le=1)
    classroom_noise_sensitivity: float = Field(ge=0, le=1)


class RedTeamPersona(BaseModel):
    persona_id: str
    role: str
    rejection_bias: float = Field(ge=0, le=1)
