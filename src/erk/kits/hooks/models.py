"""Pydantic models for Claude Code hooks configuration."""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HookEntry(BaseModel):
    """Represents a hook entry in settings.json."""

    model_config = ConfigDict(frozen=True)

    type: str = Field(default="command", pattern="^(command|prompt)$")
    command: str = Field(..., min_length=1)
    timeout: int = Field(default=30, gt=0)


class MatcherGroup(BaseModel):
    """Groups hooks under a matcher pattern."""

    model_config = ConfigDict(frozen=True)

    matcher: str = Field(..., min_length=1)
    hooks: list[HookEntry]


class ClaudeSettings(BaseModel):
    """Top-level settings.json structure with hooks configuration.

    Uses extra="allow" to preserve unknown fields when reading and writing.
    """

    model_config = ConfigDict(extra="allow")

    permissions: dict[str, Any] | None = None
    hooks: dict[str, list[MatcherGroup]] | None = None


class HookDefinition(BaseModel):
    """Represents a hook definition in kit.toml manifest."""

    model_config = ConfigDict(frozen=True)

    # Valid Claude Code lifecycle events
    VALID_LIFECYCLES: ClassVar[set[str]] = {
        "PreToolUse",
        "PostToolUse",
        "PostCustomToolCall",
        "Notification",
        "UserPromptSubmit",
        "Stop",
        "SubagentStop",
        "PreCompact",
        "SessionStart",
        "SessionEnd",
    }

    id: str = Field(..., min_length=1)
    lifecycle: str = Field(..., min_length=1)
    matcher: str | None = Field(default=None)
    invocation: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    timeout: int = Field(default=30, gt=0)

    @field_validator("lifecycle")
    @classmethod
    def validate_lifecycle(cls, v: str) -> str:
        """Validate lifecycle is a valid Claude Code event name."""
        if not v or not v.strip():
            raise ValueError("lifecycle must be a non-empty string")
        if v not in cls.VALID_LIFECYCLES:
            valid_names = ", ".join(sorted(cls.VALID_LIFECYCLES))
            raise ValueError(f"lifecycle must be one of: {valid_names}. Got: {v}")
        return v

    @field_validator("invocation")
    @classmethod
    def validate_invocation(cls, v: str) -> str:
        """Validate invocation is non-empty string."""
        if not v or not v.strip():
            raise ValueError("invocation must be a non-empty string")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is non-empty string."""
        if not v or not v.strip():
            raise ValueError("description must be a non-empty string")
        return v
