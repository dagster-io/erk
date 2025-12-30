"""Load and save artifact state from .erk/state.toml."""

from pathlib import Path

import tomli
import tomli_w

from erk.artifacts.models import ArtifactState


def _state_file_path(project_dir: Path) -> Path:
    """Return path to state file."""
    return project_dir / ".erk" / "state.toml"


def load_artifact_state(project_dir: Path) -> ArtifactState | None:
    """Load artifact state from .erk/state.toml.

    Returns None if the state file doesn't exist or has no artifacts section.
    """
    path = _state_file_path(project_dir)
    if not path.exists():
        return None

    with path.open("rb") as f:
        data = tomli.load(f)

    if "artifacts" not in data:
        return None

    artifacts_data = data["artifacts"]
    if "version" not in artifacts_data:
        return None

    return ArtifactState(version=artifacts_data["version"])


def save_artifact_state(project_dir: Path, state: ArtifactState) -> None:
    """Save artifact state to .erk/state.toml.

    Creates the .erk/ directory and state.toml file if they don't exist.
    Preserves other sections in the file if it already exists.
    """
    path = _state_file_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing data to preserve other sections
    existing_data: dict[str, object] = {}
    if path.exists():
        with path.open("rb") as f:
            existing_data = tomli.load(f)

    # Update artifacts section
    existing_data["artifacts"] = {"version": state.version}

    with path.open("wb") as f:
        tomli_w.dump(existing_data, f)
