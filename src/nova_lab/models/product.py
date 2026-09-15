from pydantic import BaseModel


class ProductVariant(BaseModel):
    variant_id: str
    label: str
    description: str
    audio_first: bool
    ai_q_and_a: bool
    curiosity_mode: bool
    learning_first: bool
    privacy_first: bool
    education_story: bool
