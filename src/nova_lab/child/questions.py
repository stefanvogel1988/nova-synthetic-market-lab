"""Synthetic question events used by the child-use state machine."""

from typing import Literal

from pydantic import BaseModel


class ChildQuestion(BaseModel):
    """A simulated interaction event, not a record of a real child's question."""

    prompt: str
    kind: Literal["new", "follow_up", "help"] = "new"
