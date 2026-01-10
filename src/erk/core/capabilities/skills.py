"""Skill-based capabilities for erk init.

Each skill capability wraps a Claude skill from .claude/skills/ and makes it
installable via the capability system.
"""

from erk.core.capabilities.skill_capability import SkillCapability


class DignifiedPythonCapability(SkillCapability):
    """Python coding standards skill (LBYL, modern types, ABCs)."""

    @property
    def skill_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Python coding standards (LBYL, modern types, ABCs)"


class FakeDrivenTestingCapability(SkillCapability):
    """5-layer test architecture with fakes."""

    @property
    def skill_name(self) -> str:
        return "fake-driven-testing"

    @property
    def description(self) -> str:
        return "5-layer test architecture with fakes"
