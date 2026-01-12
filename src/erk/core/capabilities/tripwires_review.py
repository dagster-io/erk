"""TripwiresReviewCapability - GitHub workflow for tripwire code review.

This capability installs the GitHub Actions workflow that performs automated
code review on pull requests based on tripwire patterns defined in docs/learned/tripwires.md.
"""

import shutil
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)


class TripwiresReviewCapability(Capability):
    """GitHub Action for tripwire code review.

    Installs:
    - .github/workflows/tripwires-review.yml (workflow)
    - .github/prompts/tripwires-review.md (prompt)
    """

    @property
    def name(self) -> str:
        return "tripwires-review"

    @property
    def description(self) -> str:
        return "GitHub Action for tripwire code review"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/tripwires-review.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/tripwires-review.yml",
                artifact_type="file",
            ),
            CapabilityArtifact(
                path=".github/prompts/tripwires-review.md",
                artifact_type="file",
            ),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare workflow and prompt as managed artifacts."""
        return [
            ManagedArtifact(name="tripwires-review", artifact_type="workflow"),
            ManagedArtifact(name="tripwires-review", artifact_type="prompt"),
        ]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the workflow file exists."""
        if repo_root is None:
            raise ValueError("TripwiresReviewCapability requires repo_root")
        return (repo_root / ".github" / "workflows" / "tripwires-review.yml").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the workflow and prompt."""
        if repo_root is None:
            raise ValueError("TripwiresReviewCapability requires repo_root")
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.sync import get_bundled_github_dir

        bundled_github_dir = get_bundled_github_dir()

        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        installed_count = 0

        # 1. Install tripwires-review.yml workflow
        workflow_src = bundled_github_dir / "workflows" / "tripwires-review.yml"
        if workflow_src.exists():
            workflow_dst = repo_root / ".github" / "workflows" / "tripwires-review.yml"
            workflow_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workflow_src, workflow_dst)
            installed_count += 1

        # 2. Install tripwires-review.md prompt
        prompt_src = bundled_github_dir / "prompts" / "tripwires-review.md"
        if prompt_src.exists():
            prompt_dst = repo_root / ".github" / "prompts" / "tripwires-review.md"
            prompt_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(prompt_src, prompt_dst)
            installed_count += 1

        if installed_count == 0:
            return CapabilityResult(
                success=False,
                message="No tripwires-review artifacts found in erk package",
            )

        return CapabilityResult(
            success=True,
            message=f"Installed tripwires-review ({installed_count} artifacts)",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove the tripwires-review workflow and prompt."""
        if repo_root is None:
            raise ValueError("TripwiresReviewCapability requires repo_root")

        removed: list[str] = []

        # Remove workflow
        workflow_file = repo_root / ".github" / "workflows" / "tripwires-review.yml"
        if workflow_file.exists():
            workflow_file.unlink()
            removed.append(".github/workflows/tripwires-review.yml")

        # Remove prompt
        prompt_file = repo_root / ".github" / "prompts" / "tripwires-review.md"
        if prompt_file.exists():
            prompt_file.unlink()
            removed.append(".github/prompts/tripwires-review.md")

        if not removed:
            return CapabilityResult(
                success=True,
                message="tripwires-review not installed",
            )

        return CapabilityResult(
            success=True,
            message=f"Removed {', '.join(removed)}",
        )
