"""Bundled skill capabilities — static dict + factory.

All simple skill capabilities (those that only need a name and description)
are registered here via BUNDLED_SKILLS dict. The factory function creates
concrete SkillCapability instances for each entry.

Skills with custom install/uninstall logic (like learned-docs) are NOT here;
they have their own capability classes.
"""

from erk.core.capabilities.skill_capability import SkillCapability

BUNDLED_SKILLS: dict[str, str] = {
    "dignified-python": "Python coding standards (LBYL, modern types, ABCs)",
    "fake-driven-testing": "5-layer test architecture with fakes",
    "erk-diff-analysis": "Code diff analysis for commit messages",
    "erk-exec": "Erk exec subcommand reference",
    "erk-planning": "Plan issue management",
    "objective": "Objective tracking and management",
    "gh": "GitHub CLI integration",
    "gt": "Graphite stacked PR management",
    "dignified-code-simplifier": "Code simplification review",
    "pr-operations": "Pull request operations",
    "pr-feedback-classifier": "PR feedback classification",
}


class BundledSkillCapability(SkillCapability):
    """Concrete SkillCapability for skills registered via BUNDLED_SKILLS dict."""

    def __init__(self, *, _skill_name: str, _description: str) -> None:
        self.__skill_name = _skill_name
        self.__description = _description

    @property
    def skill_name(self) -> str:
        return self.__skill_name

    @property
    def description(self) -> str:
        return self.__description


def create_bundled_skill_capabilities() -> list[SkillCapability]:
    """Create SkillCapability instances for all bundled skills."""
    return [
        BundledSkillCapability(_skill_name=name, _description=desc)
        for name, desc in BUNDLED_SKILLS.items()
    ]
