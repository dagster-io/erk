"""CodeReviewsSystemCapability - unified code review workflow infrastructure.

This capability installs the GitHub Actions workflow infrastructure that enables
convention-based code reviews. Individual review definitions are installed
separately via review-* capabilities.

Installs:
- .github/workflows/code-reviews.yml (unified workflow)
- .github/actions/setup-claude-code/ (Claude Code binary installer)
- .github/actions/setup-claude-erk/ (erk tool installer)
- Creates empty .claude/reviews/ directory
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


class CodeReviewsSystemCapability(Capability):
    """GitHub Actions infrastructure for convention-based code reviews.

    Installs:
    - .github/workflows/code-reviews.yml (unified workflow)
    - .github/actions/setup-claude-code/ (Claude Code binary installer)
    - .github/actions/setup-claude-erk/ (erk tool installer)
    - Creates empty .claude/reviews/ directory
    """

    @property
    def name(self) -> str:
        return "code-reviews-system"

    @property
    def description(self) -> str:
        return "GitHub Actions infrastructure for convention-based code reviews"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/code-reviews.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/code-reviews.yml",
                artifact_type="file",
            ),
            CapabilityArtifact(
                path=".github/actions/setup-claude-code/",
                artifact_type="directory",
            ),
            CapabilityArtifact(
                path=".github/actions/setup-claude-erk/",
                artifact_type="directory",
            ),
            CapabilityArtifact(
                path=".claude/reviews/",
                artifact_type="directory",
            ),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare workflow and actions as managed artifacts."""
        return [
            ManagedArtifact(name="code-reviews", artifact_type="workflow"),
            ManagedArtifact(name="setup-claude-code", artifact_type="action"),
            ManagedArtifact(name="setup-claude-erk", artifact_type="action"),
        ]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the workflow file exists."""
        if repo_root is None:
            return False
        return (repo_root / ".github" / "workflows" / "code-reviews.yml").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the workflow and supporting actions."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="CodeReviewsSystemCapability requires repo_root",
            )
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.state import add_installed_capability
        from erk.artifacts.sync import get_bundled_github_dir

        bundled_github_dir = get_bundled_github_dir()

        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        installed_items: list[str] = []

        # 1. Install code-reviews.yml workflow
        workflow_src = bundled_github_dir / "workflows" / "code-reviews.yml"
        if workflow_src.exists():
            workflow_dst = repo_root / ".github" / "workflows" / "code-reviews.yml"
            workflow_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workflow_src, workflow_dst)
            installed_items.append("code-reviews.yml")

        # 2. Install setup-claude-code action
        action_src = bundled_github_dir / "actions" / "setup-claude-code"
        if action_src.exists():
            action_dst = repo_root / ".github" / "actions" / "setup-claude-code"
            self._copy_directory(action_src, action_dst)
            installed_items.append("setup-claude-code/")

        # 3. Install setup-claude-erk action
        action_src = bundled_github_dir / "actions" / "setup-claude-erk"
        if action_src.exists():
            action_dst = repo_root / ".github" / "actions" / "setup-claude-erk"
            self._copy_directory(action_src, action_dst)
            installed_items.append("setup-claude-erk/")

        # 4. Create empty .claude/reviews/ directory
        reviews_dir = repo_root / ".claude" / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        installed_items.append(".claude/reviews/")

        if not installed_items:
            return CapabilityResult(
                success=False,
                message="No code-reviews-system artifacts found in erk package",
            )

        # Record capability installation
        add_installed_capability(repo_root, self.name)

        items_str = ", ".join(installed_items)
        return CapabilityResult(
            success=True,
            message=f"Installed code-reviews-system ({len(installed_items)} items: {items_str})",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove the code-reviews-system workflow and actions."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="CodeReviewsSystemCapability requires repo_root",
            )
        from erk.artifacts.state import remove_installed_capability

        removed: list[str] = []

        # Remove workflow
        workflow_file = repo_root / ".github" / "workflows" / "code-reviews.yml"
        if workflow_file.exists():
            workflow_file.unlink()
            removed.append("code-reviews.yml")

        # Remove setup-claude-code action
        action_dir = repo_root / ".github" / "actions" / "setup-claude-code"
        if action_dir.exists():
            shutil.rmtree(action_dir)
            removed.append("setup-claude-code/")

        # Remove setup-claude-erk action
        action_dir = repo_root / ".github" / "actions" / "setup-claude-erk"
        if action_dir.exists():
            shutil.rmtree(action_dir)
            removed.append("setup-claude-erk/")

        # Note: We don't remove .claude/reviews/ as it may contain user-installed reviews

        remove_installed_capability(repo_root, self.name)

        if not removed:
            return CapabilityResult(
                success=True,
                message="code-reviews-system not installed",
            )

        return CapabilityResult(
            success=True,
            message=f"Removed {', '.join(removed)}",
        )

    def _copy_directory(self, source: Path, target: Path) -> None:
        """Copy directory contents recursively."""
        target.mkdir(parents=True, exist_ok=True)
        for source_path in source.rglob("*"):
            if source_path.is_file():
                relative = source_path.relative_to(source)
                target_path = target / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
