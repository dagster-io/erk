"""Check artifact staleness by comparing installed vs current erk version."""

from pathlib import Path

from erk.artifacts.models import StalenessResult
from erk.artifacts.state import load_artifact_state
from erk.core.release_notes import get_current_version


def check_staleness(project_dir: Path) -> StalenessResult:
    """Check if artifacts are stale compared to current erk version.

    Returns a StalenessResult with:
    - is_stale: True if artifacts need to be synced
    - reason: "not-initialized", "version-mismatch", or "up-to-date"
    - current_version: The installed erk package version
    - installed_version: The version artifacts were last synced from (or None)
    """
    current_version = get_current_version()
    state = load_artifact_state(project_dir)

    if state is None:
        return StalenessResult(
            is_stale=True,
            reason="not-initialized",
            current_version=current_version,
            installed_version=None,
        )

    if state.version != current_version:
        return StalenessResult(
            is_stale=True,
            reason="version-mismatch",
            current_version=current_version,
            installed_version=state.version,
        )

    return StalenessResult(
        is_stale=False,
        reason="up-to-date",
        current_version=current_version,
        installed_version=state.version,
    )
