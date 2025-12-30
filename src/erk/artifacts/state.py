"""State file I/O for .erk/state.toml."""

from pathlib import Path

import tomli
import tomli_w

from erk.artifacts.models import ArtifactState


def get_state_path(project_dir: Path) -> Path:
    """Get path to state.toml file."""
    return project_dir / ".erk" / "state.toml"


def load_artifact_state(project_dir: Path) -> ArtifactState | None:
    """Load state from .erk/state.toml.

    Returns None if file does not exist.
    """
    path = get_state_path(project_dir)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = tomli.load(f)
        return ArtifactState(version=data["artifacts"]["version"])


def save_artifact_state(project_dir: Path, state: ArtifactState) -> None:
    """Save state to .erk/state.toml."""
    path = get_state_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"artifacts": {"version": state.version}}
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
