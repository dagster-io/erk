"""Base class for review-based capabilities.

ReviewCapability wraps the artifact sync system to install code review definitions
to external repositories via the capability system.
"""

from abc import abstractmethod
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)


class ReviewCapability(Capability):
    """Base class for capabilities that install a single code review definition.

    Reviews are installed to .claude/reviews/ in the target project.
    Subclasses only need to implement review_name and description.

    Requires: code-reviews-system capability (checked in preflight)
    """

    @property
    @abstractmethod
    def review_name(self) -> str:
        """Name of the review file (without .md extension)."""
        ...

    @property
    def name(self) -> str:
        """CLI-facing identifier - prefixed with 'review-'."""
        return f"review-{self.review_name}"

    @property
    def scope(self) -> CapabilityScope:
        """Reviews are project-level capabilities."""
        return "project"

    @property
    def installation_check_description(self) -> str:
        """Human-readable description of what is_installed() checks."""
        return f".claude/reviews/{self.review_name}.md file exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        """List of artifacts this capability installs."""
        return [
            CapabilityArtifact(
                path=f".claude/reviews/{self.review_name}.md",
                artifact_type="file",
            )
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare the review as a managed artifact."""
        return [ManagedArtifact(name=self.review_name, artifact_type="review")]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the review file exists."""
        if repo_root is None:
            return False
        return (repo_root / ".claude" / "reviews" / f"{self.review_name}.md").exists()

    def preflight(self, repo_root: Path | None) -> CapabilityResult:
        """Check that code-reviews-system capability is installed."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="ReviewCapability requires repo_root",
            )

        # Check for code-reviews-system by looking for the workflow
        workflow_path = repo_root / ".github" / "workflows" / "code-reviews.yml"
        if not workflow_path.exists():
            return CapabilityResult(
                success=False,
                message="Requires 'code-reviews-system' capability to be installed first",
            )
        return CapabilityResult(success=True, message="")

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the review using bundled artifacts."""
        import shutil

        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="ReviewCapability requires repo_root",
            )
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.state import add_installed_capability
        from erk.artifacts.sync import get_bundled_github_dir

        review_file = repo_root / ".claude" / "reviews" / f"{self.review_name}.md"
        if review_file.exists():
            # Still record installation even if file exists
            add_installed_capability(repo_root, self.name)
            return CapabilityResult(
                success=True,
                message=f".claude/reviews/{self.review_name}.md already exists",
            )

        bundled_github_dir = get_bundled_github_dir()
        source_review = bundled_github_dir / "reviews" / f"{self.review_name}.md"

        if not source_review.exists():
            return CapabilityResult(
                success=False,
                message=f"Review '{self.review_name}' not found in erk package",
            )

        # Copy review file
        review_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_review, review_file)

        # Record capability installation
        add_installed_capability(repo_root, self.name)

        return CapabilityResult(
            success=True,
            message=f"Installed .claude/reviews/{self.review_name}.md",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Uninstall the review by deleting its file."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="ReviewCapability requires repo_root",
            )
        from erk.artifacts.state import remove_installed_capability

        review_file = repo_root / ".claude" / "reviews" / f"{self.review_name}.md"
        if not review_file.exists():
            # Still remove from installed capabilities
            remove_installed_capability(repo_root, self.name)
            return CapabilityResult(
                success=True,
                message=f".claude/reviews/{self.review_name}.md does not exist",
            )

        review_file.unlink()
        # Remove from installed capabilities
        remove_installed_capability(repo_root, self.name)
        return CapabilityResult(
            success=True,
            message=f"Removed .claude/reviews/{self.review_name}.md",
        )
