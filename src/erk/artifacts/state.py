"""Load and save artifact state from .erk/state.toml."""

from pathlib import Path
from typing import Any

import tomli
import tomli_w

from erk.artifacts.models import ArtifactFileState, ArtifactState


def _state_file_path(project_dir: Path) -> Path:
    """Return path to state file."""
    return project_dir / ".erk" / "state.toml"


def load_artifact_state(project_dir: Path) -> ArtifactState | None:
    """Load artifact state from .erk/state.toml.

    Returns None if the state file doesn't exist, has no artifacts section,
    or is missing the required files section.

    Format:
        [artifacts]
        version = "0.3.1"

        [artifacts.files."skills/dignified-python"]
        version = "0.3.0"
        hash = "a1b2c3d4e5f6g7h8"
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

    # Require files section
    if "files" not in artifacts_data:
        return None

    files: dict[str, ArtifactFileState] = {}
    files_data = artifacts_data["files"]

    for artifact_path, file_data in files_data.items():
        if isinstance(file_data, dict) and "version" in file_data and "hash" in file_data:
            files[artifact_path] = ArtifactFileState(
                version=file_data["version"],
                hash=file_data["hash"],
            )

    return ArtifactState(version=artifacts_data["version"], files=files)


def save_artifact_state(project_dir: Path, state: ArtifactState) -> None:
    """Save artifact state to .erk/state.toml.

    Creates the .erk/ directory and state.toml file if they don't exist.
    Preserves other sections in the file if it already exists.

    Format:
        [artifacts]
        version = "0.3.1"

        [artifacts.files."skills/dignified-python"]
        version = "0.3.0"
        hash = "a1b2c3d4e5f6g7h8"
    """
    path = _state_file_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing data to preserve other sections
    existing_data: dict[str, Any] = {}
    if path.exists():
        with path.open("rb") as f:
            existing_data = tomli.load(f)

    # Build files section
    files_data: dict[str, dict[str, str]] = {}
    for artifact_path, file_state in state.files.items():
        files_data[artifact_path] = {
            "version": file_state.version,
            "hash": file_state.hash,
        }

    # Update artifacts section
    existing_data["artifacts"] = {
        "version": state.version,
        "files": files_data,
    }

    with path.open("wb") as f:
        tomli_w.dump(existing_data, f)
