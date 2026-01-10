"""Workflow-based capabilities for erk init.

Workflow capabilities install GitHub Actions workflows and related actions.
"""

import shutil
from pathlib import Path

from erk.core.capabilities.base import Capability, CapabilityArtifact, CapabilityResult


class ErkImplWorkflowCapability(Capability):
    """GitHub Action for automated implementation workflow.

    Installs:
    - .github/workflows/erk-impl.yml
    - .github/actions/setup-claude-code/
    - .github/actions/setup-claude-erk/
    """

    @property
    def name(self) -> str:
        return "erk-impl-workflow"

    @property
    def description(self) -> str:
        return "GitHub Action for automated implementation"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/erk-impl.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/erk-impl.yml",
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
        ]

    def is_installed(self, repo_root: Path) -> bool:
        """Check if the workflow file exists."""
        return (repo_root / ".github" / "workflows" / "erk-impl.yml").exists()

    def install(self, repo_root: Path) -> CapabilityResult:
        """Install the workflow and related actions."""
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.sync import get_bundled_github_dir

        bundled_github_dir = get_bundled_github_dir()
        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        installed_count = 0

        # Install workflow
        workflow_src = bundled_github_dir / "workflows" / "erk-impl.yml"
        if workflow_src.exists():
            workflow_dst = repo_root / ".github" / "workflows" / "erk-impl.yml"
            workflow_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workflow_src, workflow_dst)
            installed_count += 1

        # Install actions
        actions = ["setup-claude-code", "setup-claude-erk"]
        for action_name in actions:
            action_src = bundled_github_dir / "actions" / action_name
            if action_src.exists():
                action_dst = repo_root / ".github" / "actions" / action_name
                action_dst.mkdir(parents=True, exist_ok=True)
                self._copy_directory(action_src, action_dst)
                installed_count += 1

        if installed_count == 0:
            return CapabilityResult(
                success=False,
                message="No workflow artifacts found in erk package",
            )

        return CapabilityResult(
            success=True,
            message=f"Installed erk-impl workflow ({installed_count} artifacts)",
        )

    def _copy_directory(self, source: Path, target: Path) -> None:
        """Copy directory contents recursively."""
        for source_path in source.rglob("*"):
            if source_path.is_file():
                relative = source_path.relative_to(source)
                target_path = target / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
