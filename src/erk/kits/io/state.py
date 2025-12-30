"""State file I/O for kits.toml."""

from pathlib import Path

import tomli
import tomli_w

from erk.kits.cli.output import user_output
from erk.kits.models.config import InstalledKit, ProjectConfig


def _find_config_path(project_dir: Path) -> Path | None:
    """Find kits.toml config file.

    Args:
        project_dir: Project root directory

    Returns:
        Path to config file if found, None otherwise
    """
    config_path = project_dir / ".erk" / "kits.toml"
    if config_path.exists():
        return config_path
    return None


def load_project_config(project_dir: Path) -> ProjectConfig | None:
    """Load kits.toml from project directory.

    Checks .erk/kits.toml for kit configuration.

    Returns None if file doesn't exist.
    """
    config_path = _find_config_path(project_dir)
    if config_path is None:
        return None

    with open(config_path, "rb") as f:
        data = tomli.load(f)

    # Parse kits
    kits: dict[str, InstalledKit] = {}
    if "kits" in data:
        for kit_name, kit_data in data["kits"].items():
            # Require kit_id field (no fallback)
            if "kit_id" not in kit_data:
                msg = f"Kit configuration missing required 'kit_id' field: {kit_name}"
                raise KeyError(msg)
            kit_id = kit_data["kit_id"]

            # Require source_type field (no fallback)
            if "source_type" not in kit_data:
                msg = f"Kit configuration missing required 'source_type' field: {kit_name}"
                raise KeyError(msg)
            source_type = kit_data["source_type"]

            kits[kit_name] = InstalledKit(
                kit_id=kit_id,
                source_type=source_type,
                version=kit_data["version"],
                artifacts=kit_data["artifacts"],
            )

    return ProjectConfig(
        version=data.get("version", "1"),
        kits=kits,
    )


def require_project_config(project_dir: Path) -> ProjectConfig:
    """Load kits.toml and exit with error if not found.

    This is a convenience wrapper around load_project_config that enforces
    the config must exist, displaying a helpful error message if not.

    Returns:
        ProjectConfig if found

    Raises:
        SystemExit: If kits.toml not found
    """
    config = load_project_config(project_dir)
    if config is None:
        msg = "Error: No .erk/kits.toml found. Run 'erk init' to create one."
        user_output(msg)
        raise SystemExit(1)
    return config


def save_project_config(project_dir: Path, config: ProjectConfig) -> None:
    """Save kits.toml to .erk/ directory.

    Always saves to .erk/kits.toml.
    Creates .erk/ directory if it doesn't exist.
    """
    erk_dir = project_dir / ".erk"
    if not erk_dir.exists():
        erk_dir.mkdir(parents=True)
    config_path = erk_dir / "kits.toml"

    # Convert ProjectConfig to dict
    data = {
        "version": config.version,
        "kits": {},
    }

    for kit_id, kit in config.kits.items():
        data["kits"][kit_id] = {
            "kit_id": kit.kit_id,
            "source_type": kit.source_type,
            "version": kit.version,
            "artifacts": kit.artifacts,
        }

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def create_default_config() -> ProjectConfig:
    """Create default project configuration."""
    return ProjectConfig(
        version="1",
        kits={},
    )
