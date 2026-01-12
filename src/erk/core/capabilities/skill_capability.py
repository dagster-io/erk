"""Base class for skill-based capabilities.

SkillCapability wraps the existing artifact sync system to install Claude skills
to external repositories via the capability system.
"""

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)

if TYPE_CHECKING:
    pass


class SkillCapability(Capability):
    """Base class for capabilities that install a single skill.

    Subclasses only need to implement skill_name and description.
    The base class handles artifact tracking and installation via artifact sync.
    """

    @property
    @abstractmethod
    def skill_name(self) -> str:
        """Name of the skill directory in .claude/skills/."""
        ...

    @property
    def name(self) -> str:
        """CLI-facing identifier - same as skill name."""
        return self.skill_name

    @property
    def scope(self) -> CapabilityScope:
        """Skills are project-level capabilities."""
        return "project"

    @property
    def installation_check_description(self) -> str:
        """Human-readable description of what is_installed() checks."""
        return f".claude/skills/{self.skill_name}/ directory exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        """List of artifacts this capability installs."""
        return [
            CapabilityArtifact(
                path=f".claude/skills/{self.skill_name}/",
                artifact_type="directory",
            )
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare the skill as a managed artifact."""
        return [ManagedArtifact(name=self.skill_name, artifact_type="skill")]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the skill directory exists."""
        assert repo_root is not None, "SkillCapability requires repo_root"
        return (repo_root / ".claude" / "skills" / self.skill_name).exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the skill using artifact sync."""
        assert repo_root is not None, "SkillCapability requires repo_root"
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.sync import get_bundled_claude_dir

        skill_dir = repo_root / ".claude" / "skills" / self.skill_name
        if skill_dir.exists():
            return CapabilityResult(
                success=True,
                message=f".claude/skills/{self.skill_name}/ already exists",
            )

        bundled_claude_dir = get_bundled_claude_dir()
        source_skill = bundled_claude_dir / "skills" / self.skill_name

        if not source_skill.exists():
            return CapabilityResult(
                success=False,
                message=f"Skill '{self.skill_name}' not found in erk package",
            )

        # Copy skill directory
        skill_dir.mkdir(parents=True, exist_ok=True)
        self._copy_directory(source_skill, skill_dir)

        return CapabilityResult(
            success=True,
            message=f"Installed .claude/skills/{self.skill_name}/",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Uninstall the skill by deleting its directory."""
        assert repo_root is not None, "SkillCapability requires repo_root"
        import shutil

        skill_dir = repo_root / ".claude" / "skills" / self.skill_name
        if not skill_dir.exists():
            return CapabilityResult(
                success=True,
                message=f".claude/skills/{self.skill_name}/ does not exist",
            )

        shutil.rmtree(skill_dir)
        return CapabilityResult(
            success=True,
            message=f"Removed .claude/skills/{self.skill_name}/",
        )

    def _copy_directory(self, source: Path, target: Path) -> None:
        """Copy directory contents recursively."""
        import shutil

        for source_path in source.rglob("*"):
            if source_path.is_file():
                relative = source_path.relative_to(source)
                target_path = target / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
