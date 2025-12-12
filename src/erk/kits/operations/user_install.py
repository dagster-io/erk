"""Project directory installation operations."""

from pathlib import Path

from erk.kits.models.config import InstalledKit
from erk.kits.models.installation import InstallationContext
from erk.kits.operations.install import install_kit as install_kit_base
from erk.kits.sources.resolver import ResolvedKit


def install_kit_to_project(
    resolved: ResolvedKit,
    context: InstallationContext,
    overwrite: bool = False,
    filtered_artifacts: dict[str, list[str]] | None = None,
) -> InstalledKit:
    """Install a kit to project directory.

    Args:
        resolved: Resolved kit to install
        context: Installation context
        overwrite: Whether to overwrite existing files
        filtered_artifacts: Optional filtered artifacts (from ArtifactSpec.filter_artifacts())

    Returns:
        InstalledKit with installation metadata
    """
    return install_kit_base(resolved, context.base_path, overwrite, filtered_artifacts)


def get_installation_context(project_dir: Path | None = None) -> InstallationContext:
    """Create installation context for the project.

    Args:
        project_dir: Project directory (defaults to current working directory)

    Returns:
        InstallationContext configured for the project
    """
    if project_dir is None:
        project_dir = Path.cwd()
    return InstallationContext(project_dir)
