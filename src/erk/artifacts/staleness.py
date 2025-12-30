"""Staleness detection for artifact sync."""

import importlib.metadata
from pathlib import Path

from erk.artifacts.models import StalenessResult
from erk.artifacts.state import load_artifact_state


def get_current_version() -> str:
    """Get the currently installed version of erk."""
    return importlib.metadata.version("erk")


def check_staleness(project_dir: Path) -> StalenessResult:
    """Check if artifacts are stale."""
    state = load_artifact_state(project_dir)
    current_version = get_current_version()

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
