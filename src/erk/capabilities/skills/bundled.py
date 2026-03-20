"""Bundled skill capabilities — cached factory.

All simple skill capabilities (those that only need a name and description)
are registered here. The dict is created lazily via a cached function to
avoid module-import-time allocation.

Skills with custom install/uninstall logic (like learned-docs) are NOT here;
they have their own capability classes.
"""

from functools import cache

from erk.core.capabilities.codex_portable import codex_portable_skills
from erk.core.capabilities.skill_capability import SkillCapability
from erk_shared.context.types import AgentBackend

_UNBUNDLED_SKILLS: frozenset[str] = frozenset(
    {
        "ci-iteration",
        "cli-skill-creator",
        "cmux",
        "command-creator",
        # npx-managed: as skills migrate to npx distribution, they move from
        # bundled_skills() to _UNBUNDLED_SKILLS and can be removed from
        # codex_portable_skills() and pyproject.toml force-include.
        "dignified-python",  # npx-managed
        "fake-driven-testing",  # npx-managed
        "learned-docs",  # has its own capability class (LearnedDocsCapability)
        "npx-skills",
        "refac-cli-push-down",
        "fdt-refactor-mock-to-fake",
        "refac-module-to-subpackage",
        "rename-swarm",
        "session-inspector",
        "erk-skill-onboarding",
        "skill-creator",
    }
)

_REQUIRED_BUNDLED_SKILLS: frozenset[str] = frozenset(
    {
        "erk-diff-analysis",
        "erk-exec",
        "objective",
        "pr-operations",
        "pr-feedback-classifier",
    }
)


@cache
def bundled_skills() -> dict[str, str]:
    """Return the bundled skills dict. Cached to avoid re-creation."""
    return {
        "erk-diff-analysis": "Code diff analysis for commit messages",
        "erk-exec": "Erk exec subcommand reference",
        "objective": "Objective tracking and management",
        "gh": "GitHub CLI integration",
        "gt": "Graphite stacked PR management",
        "dignified-code-simplifier": "Code simplification review",
        "pr-operations": "Pull request operations",
        "pr-feedback-classifier": "PR feedback classification",
        # Tombstone: overwrites stale skill in customer repos on next sync
        "erk-planning": "[REMOVED] Plan management now in slash commands",
    }


def unbundled_skills() -> frozenset[str]:
    """Skills in .claude/skills/ that are intentionally not bundled with erk."""
    return _UNBUNDLED_SKILLS


def is_required_bundled_skill(skill_name: str) -> bool:
    """Return True if the given skill name is a required bundled skill."""
    return skill_name in _REQUIRED_BUNDLED_SKILLS


class BundledSkillCapability(SkillCapability):
    """Concrete SkillCapability for skills registered via bundled_skills() dict."""

    def __init__(self, *, _skill_name: str, _description: str) -> None:
        self._skill_name = _skill_name
        self._description = _description

    @property
    def skill_name(self) -> str:
        return self._skill_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def required(self) -> bool:
        return self._skill_name in _REQUIRED_BUNDLED_SKILLS

    @property
    def supported_backends(self) -> tuple[AgentBackend, ...]:
        if self.skill_name in codex_portable_skills():
            return ("claude", "codex")
        return ("claude",)


def create_bundled_skill_capabilities() -> list[SkillCapability]:
    """Create SkillCapability instances for all bundled skills."""
    return [
        BundledSkillCapability(_skill_name=name, _description=desc)
        for name, desc in bundled_skills().items()
    ]
