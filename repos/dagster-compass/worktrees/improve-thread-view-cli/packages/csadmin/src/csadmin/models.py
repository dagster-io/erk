"""Pydantic models for context store validation."""

from pydantic import BaseModel, Field


class ContextStoreProject(BaseModel):
    """Context store project configuration model."""

    project_name: str = Field(pattern=r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$")
    teams: dict[str, list[str]] = Field(default_factory=dict)
    version: int = Field(
        default=1, description="Context store layout version (1=legacy, 2=manifest)"
    )


class ProvidedContext(BaseModel):
    """Learning/feedback context model."""

    topic: str
    incorrect_understanding: str
    correct_understanding: str
    search_keywords: str


class UserCronJob(BaseModel, frozen=True):
    """Scheduled query job model."""

    cron: str
    question: str
    thread: str
