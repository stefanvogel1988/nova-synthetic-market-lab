from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LabSettings(BaseModel):
    seed: int = 20260915
    parent_count: int = Field(default=150, ge=1)
    child_count: int = Field(default=30, ge=1)
    education_count: int = Field(default=20, ge=1)
    red_team_count: int = Field(default=12, ge=1)
    output_dir: Path = Path("outputs")

    @classmethod
    def load(cls, path: Path) -> "LabSettings":
        return cls.model_validate(yaml.safe_load(path.read_text()) or {})

    def make_run_id(self) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"nova-{stamp}-s{self.seed}"
