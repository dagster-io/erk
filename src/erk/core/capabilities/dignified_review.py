"""DignifiedReviewCapability - GitHub workflow for Python code review.

This capability installs the GitHub Actions workflow that performs automated
code review on pull requests.

Note: Requires the 'dignified-python' capability to be installed first,
as the workflow depends on the dignified-python skill being present.
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

    Requires: dignified-python capability (checked in preflight)

    Installs:
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
        if repo_root is None:
            raise ValueError("DignifiedReviewCapability requires repo_root")
        return (repo_root / ".github" / "workflows" / "dignified-python-review.yml").exists()

    def preflight(self, repo_root: Path | None) -> CapabilityResult:
        """Check that dignified-python skill is installed."""
        if repo_root is None:
            raise ValueError("DignifiedReviewCapability requires repo_root")
        skill_path = repo_root / ".claude" / "skills" / "dignified-python"
        if not skill_path.exists():
            return CapabilityResult(
                success=False,
                message="Requires 'dignified-python' capability to be installed first",
            )
        return CapabilityResult(success=True, message="")

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the workflow and prompt."""
        if repo_root is None:
            raise ValueError("DignifiedReviewCapability requires repo_root")
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.sync import get_bundled_github_dir

        bundled_github_dir = get_bundled_github_dir()

        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        installed_count = 0

        # 1. Install dignified-python-review.yml workflow
        workflow_src = bundled_github_dir / "workflows" / "dignified-python-review.yml"
        if workflow_src.exists():
            workflow_dst = repo_root / ".github" / "workflows" / "dignified-python-review.yml"
            workflow_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workflow_src, workflow_dst)
            installed_count += 1

        # 2. Install dignified-python-review.md prompt
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
