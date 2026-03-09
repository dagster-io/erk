"""Types for the Skills CLI gateway."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillsCliResult:
    """Result from a skills CLI operation."""

    success: bool
    exit_code: int
    message: str
