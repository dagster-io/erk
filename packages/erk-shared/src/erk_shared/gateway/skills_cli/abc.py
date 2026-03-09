"""Abstract interface for the vercel-labs/skills CLI."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.gateway.skills_cli.types import SkillsCliResult


class SkillsCli(ABC):
    """Gateway for the vercel-labs/skills CLI (npx skills).

    Wraps the skills CLI for discovering, installing, and removing
    agent skills from skill repositories.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if npx is available on PATH."""
        ...

    @abstractmethod
    def list_skills(self, *, source: str) -> SkillsCliResult:
        """List available skills from a source repository.

        Args:
            source: Local path or GitHub owner/repo for skill source.

        Returns:
            SkillsCliResult with stdout listing available skills.
        """
        ...

    @abstractmethod
    def add_skills(
        self,
        *,
        source: str,
        skill_names: list[str],
        agents: list[str],
        cwd: Path | None,
    ) -> SkillsCliResult:
        """Install skills from a source repository.

        Args:
            source: Local path or GitHub owner/repo for skill source.
            skill_names: Names of skills to install.
            agents: Agent backends to install for (e.g. "claude-code").
            cwd: Working directory for the skills CLI. If None, uses current directory.

        Returns:
            SkillsCliResult with installation outcome.
        """
        ...

    @abstractmethod
    def remove_skills(
        self,
        *,
        skill_names: list[str],
        agents: list[str],
        cwd: Path | None,
    ) -> SkillsCliResult:
        """Remove installed skills.

        Args:
            skill_names: Names of skills to remove.
            agents: Agent backends to remove from.
            cwd: Working directory for the skills CLI. If None, uses current directory.

        Returns:
            SkillsCliResult with removal outcome.
        """
        ...
