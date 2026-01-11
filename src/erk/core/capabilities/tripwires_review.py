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
