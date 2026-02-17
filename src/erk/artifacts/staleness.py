"""Check artifact staleness by comparing installed vs current erk version."""

from pathlib import Path

from erk.artifacts.models import StalenessResult
from erk.artifacts.paths import ErkPackageInfo
from erk.artifacts.state import load_artifact_state


def check_staleness(project_dir: Path, *, package: ErkPackageInfo) -> StalenessResult:
    """Check if artifacts are stale compared to current erk version.

    Returns a StalenessResult with:
    - is_stale: True if artifacts need to be synced
    - reason: "not-initialized", "version-mismatch", "up-to-date", or "erk-repo"
    - current_version: The installed erk package version
    - installed_version: The version artifacts were last synced from (or None)
    """
    # In erk repo, artifacts are read from source - always up to date
    # Still load state.toml to dogfood the state loading path
    if package.in_erk_repo:
        state = load_artifact_state(project_dir)
        return StalenessResult(
            is_stale=False,
            reason="erk-repo",
            current_version=package.current_version,
            installed_version=state.version if state else None,
        )

    state = load_artifact_state(project_dir)

    if state is None:
        return StalenessResult(
            is_stale=True,
            reason="not-initialized",
            current_version=package.current_version,
            installed_version=None,
        )

    if state.version != package.current_version:
        return StalenessResult(
            is_stale=True,
            reason="version-mismatch",
            current_version=package.current_version,
            installed_version=state.version,
        )

    return StalenessResult(
        is_stale=False,
        reason="up-to-date",
        current_version=package.current_version,
        installed_version=state.version,
    )
