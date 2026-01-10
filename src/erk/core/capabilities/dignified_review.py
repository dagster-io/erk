"""DignifiedReviewCapability - GitHub workflow for Python code review.

This capability installs the dignified-python skill and the GitHub Actions workflow
that performs automated code review on pull requests.
"""

import shutil
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)


class DignifiedReviewCapability(Capability):
    """GitHub Action for automated Python code review.

    Installs:
    - .claude/skills/dignified-python/ (skill)
    - .github/workflows/dignified-python-review.yml (workflow)
    - .github/prompts/dignified-python-review.md (prompt)
    """

    @property
    def name(self) -> str:
        return "dignified-review"

    @property
    def description(self) -> str:
        return "GitHub Action for Python code review"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/dignified-python-review.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".claude/skills/dignified-python/",
                artifact_type="directory",
            ),
            CapabilityArtifact(
                path=".github/workflows/dignified-python-review.yml",
                artifact_type="file",
            ),
            CapabilityArtifact(
                path=".github/prompts/dignified-python-review.md",
                artifact_type="file",
            ),
        ]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the workflow file exists."""
        assert repo_root is not None, "DignifiedReviewCapability requires repo_root"
        return (repo_root / ".github" / "workflows" / "dignified-python-review.yml").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the skill, workflow, and prompt."""
        assert repo_root is not None, "DignifiedReviewCapability requires repo_root"
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.sync import get_bundled_claude_dir, get_bundled_github_dir

        bundled_claude_dir = get_bundled_claude_dir()
        bundled_github_dir = get_bundled_github_dir()

        if not bundled_claude_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .claude/ not found in erk package",
            )

        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        installed_count = 0

        # 1. Install dignified-python skill
        skill_src = bundled_claude_dir / "skills" / "dignified-python"
        if skill_src.exists():
            skill_dst = repo_root / ".claude" / "skills" / "dignified-python"
            skill_dst.mkdir(parents=True, exist_ok=True)
            self._copy_directory(skill_src, skill_dst)
            installed_count += 1

        # 2. Install dignified-python-review.yml workflow
        workflow_src = bundled_github_dir / "workflows" / "dignified-python-review.yml"
        if workflow_src.exists():
            workflow_dst = repo_root / ".github" / "workflows" / "dignified-python-review.yml"
            workflow_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workflow_src, workflow_dst)
            installed_count += 1

        # 3. Install dignified-python-review.md prompt
        prompt_src = bundled_github_dir / "prompts" / "dignified-python-review.md"
        if prompt_src.exists():
            prompt_dst = repo_root / ".github" / "prompts" / "dignified-python-review.md"
            prompt_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(prompt_src, prompt_dst)
            installed_count += 1

        if installed_count == 0:
            return CapabilityResult(
                success=False,
                message="No dignified-review artifacts found in erk package",
            )

        return CapabilityResult(
            success=True,
            message=f"Installed dignified-review ({installed_count} artifacts)",
        )

    def _copy_directory(self, source: Path, target: Path) -> None:
        """Copy directory contents recursively."""
        for source_path in source.rglob("*"):
            if source_path.is_file():
                relative = source_path.relative_to(source)
                target_path = target / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
