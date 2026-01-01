"""Local init state model and persistence.

Manages local developer setup state stored in .erk/local-state.toml.
This file is gitignored and tracks per-developer initialization.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import tomli
import tomli_w

LOCAL_STATE_FILENAME = "local-state.toml"


@dataclass(frozen=True)
class LocalInitState:
    """Local init state for a developer's erk setup.

    Attributes:
        initialized_version: The erk version that was used to initialize this repo locally
        timestamp: ISO 8601 timestamp of when local init was performed
    """

    initialized_version: str
    timestamp: str


def get_local_state_path(repo_root: Path) -> Path:
    """Get the path to the local state file.

    Args:
        repo_root: Path to the repository root

    Returns:
        Path to .erk/local-state.toml
    """
    return repo_root / ".erk" / LOCAL_STATE_FILENAME


def load_local_state(repo_root: Path) -> LocalInitState | None:
    """Load local init state from .erk/local-state.toml.

    Args:
        repo_root: Path to the repository root

    Returns:
        LocalInitState if file exists and is valid, None otherwise
    """
    state_file = get_local_state_path(repo_root)
    if not state_file.exists():
        return None

    content = state_file.read_text(encoding="utf-8")
    data = tomli.loads(content)

    local_init = data.get("local_init")
    if local_init is None:
        return None

    initialized_version = local_init.get("initialized_version")
    timestamp = local_init.get("timestamp")

    if initialized_version is None or timestamp is None:
        return None

    return LocalInitState(
        initialized_version=initialized_version,
        timestamp=timestamp,
    )


def save_local_state(repo_root: Path, state: LocalInitState) -> None:
    """Save local init state to .erk/local-state.toml.

    Args:
        repo_root: Path to the repository root
        state: LocalInitState to save
    """
    state_file = get_local_state_path(repo_root)

    # Ensure .erk directory exists
    state_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "local_init": {
            "initialized_version": state.initialized_version,
            "timestamp": state.timestamp,
        }
    }

    content = tomli_w.dumps(data)
    state_file.write_text(content, encoding="utf-8")


def create_local_init_state(version: str) -> LocalInitState:
    """Create a new LocalInitState with current timestamp.

    Args:
        version: The erk version to record

    Returns:
        New LocalInitState with current timestamp
    """
    return LocalInitState(
        initialized_version=version,
        timestamp=datetime.now().isoformat(),
    )
