"""DignifiedPythonCapability - Python coding standards skill."""

from erk.core.capabilities.skill_capability import SkillCapability


class DignifiedPythonCapability(SkillCapability):
    """Python coding standards skill (LBYL, modern types, ABCs)."""

    @property
    def skill_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Python coding standards (LBYL, modern types, ABCs)"
