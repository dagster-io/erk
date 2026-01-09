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


class GhCapability(SkillCapability):
    """GitHub CLI skill."""

    @property
    def skill_name(self) -> str:
        return "gh"

    @property
    def description(self) -> str:
        return "GitHub CLI skill"


class GtCapability(SkillCapability):
    """Graphite stacked PR skill."""

    @property
    def skill_name(self) -> str:
        return "gt"

    @property
    def description(self) -> str:
        return "Graphite stacked PR skill"


class CommandCreatorCapability(SkillCapability):
    """Creating Claude Code slash commands."""

    @property
    def skill_name(self) -> str:
        return "command-creator"

    @property
    def description(self) -> str:
        return "Creating Claude Code slash commands"


class CliSkillCreatorCapability(SkillCapability):
    """Creating CLI tool skills."""

    @property
    def skill_name(self) -> str:
        return "cli-skill-creator"

    @property
    def description(self) -> str:
        return "Creating CLI tool skills"


class CiIterationCapability(SkillCapability):
    """Iterative CI fixing patterns."""

    @property
    def skill_name(self) -> str:
        return "ci-iteration"

    @property
    def description(self) -> str:
        return "Iterative CI fixing patterns"


# All skill capabilities for easy iteration
SKILL_CAPABILITIES: list[type[SkillCapability]] = [
    DignifiedPythonCapability,
    FakeDrivenTestingCapability,
    GhCapability,
    GtCapability,
    CommandCreatorCapability,
    CliSkillCreatorCapability,
    CiIterationCapability,
]
