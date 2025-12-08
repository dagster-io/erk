"""State file I/O for dot-agent.toml."""

from pathlib import Path

import click
import tomli
import tomli_w
from pydantic import ValidationError

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.hooks.models import HookDefinition
from dot_agent_kit.models.config import InstalledKit, ProjectConfig


def _extract_validation_error_details(error: ValidationError) -> tuple[list[str], list[str]]:
    """Extract missing and invalid field information from Pydantic ValidationError.

    Args:
        error: Pydantic ValidationError instance

    Returns:
        Tuple of (missing_fields, invalid_fields) where:
        - missing_fields: List of field names that are missing
        - invalid_fields: List of "field_name (error_type)" strings for invalid fields
    """
    missing_fields = []
    invalid_fields = []

    for err in error.errors():
        error_type = err.get("type", "")
        field_path = err.get("loc", ())
        field_name = ".".join(str(p) for p in field_path if isinstance(p, str))

        if error_type == "missing":
            missing_fields.append(field_name)
        else:
            invalid_fields.append(f"{field_name} ({error_type})")

    return missing_fields, invalid_fields


def _build_hook_validation_error_message(
    kit_name: str,
    hook_id: str,
    hook_position: int,
    total_hooks: int,
    missing_fields: list[str],
    invalid_fields: list[str],
) -> str:
    """Build user-friendly error message for hook validation failures.

    Args:
        kit_name: Name of the kit containing the invalid hook
        hook_id: ID of the hook that failed validation (or "unknown")
        hook_position: 0-based index of the hook in the list
        total_hooks: Total number of hooks in the kit
        missing_fields: List of missing required field names
        invalid_fields: List of invalid field descriptions

    Returns:
        Formatted error message string
    """
    error_lines = [f"❌ Error: Invalid hook definition in kit '{kit_name}'", ""]
    error_lines.append(f"Details: Hook ID: {hook_id}")
    error_lines.append(f"  Position: Hook #{hook_position + 1} of {total_hooks}")

    if missing_fields:
        error_lines.append(f"  Missing required fields: {', '.join(missing_fields)}")
    if invalid_fields:
        error_lines.append(f"  Invalid fields: {', '.join(invalid_fields)}")

    error_lines.extend(
        [
            "",
            "Suggested action:",
            f"  1. Run 'dot-agent kit install {kit_name}' to reinstall with correct configuration",
            "  2. Or manually edit dot-agent.toml to add missing fields",
            "  3. Check kit documentation for hook format",
        ]
    )

    return "\n".join(error_lines)


def _load_dev_mode_from_pyproject(project_dir: Path) -> bool:
    """Load dev_mode setting from pyproject.toml [tool.dot-agent] section.

    Args:
        project_dir: Project root directory

    Returns:
        True if dev_mode is enabled, False otherwise
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return False

    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)

    # Check for [tool.dot-agent] section
    if "tool" not in data:
        return False
    if "dot-agent" not in data["tool"]:
        return False

    # Get dev_mode value (default to False)
    tool_config = data["tool"]["dot-agent"]
    if "dev_mode" in tool_config:
        return bool(tool_config["dev_mode"])

    return False


def _find_config_path(project_dir: Path) -> Path | None:
    """Find config file, checking new location first then falling back to old.

    Args:
        project_dir: Project root directory

    Returns:
        Path to config file if found, None otherwise
    """
    # New location: .agent/dot-agent.toml
    new_path = project_dir / ".agent" / "dot-agent.toml"
    if new_path.exists():
        return new_path

    # Fallback: old location at project root
    old_path = project_dir / "dot-agent.toml"
    if old_path.exists():
        return old_path

    return None


def load_project_config(project_dir: Path) -> ProjectConfig | None:
    """Load dot-agent.toml from project directory.

    Checks .agent/dot-agent.toml first (new location), then falls back to
    dot-agent.toml at project root (old location) for backwards compatibility.

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
            # Parse hooks if present
            hooks: list[HookDefinition] = []
            if "hooks" in kit_data:
                for idx, hook_data in enumerate(kit_data["hooks"]):
                    try:
                        hooks.append(HookDefinition.model_validate(hook_data))
                    except ValidationError as e:
                        # Error boundary: translate Pydantic errors to user-friendly messages
                        # Extract hook ID from the specific failing hook
                        if isinstance(hook_data, dict):
                            hook_id = hook_data.get("id", "unknown")
                        else:
                            hook_id = "unknown"

                        # Extract error details and build user-friendly message
                        missing_fields, invalid_fields = _extract_validation_error_details(e)
                        msg = _build_hook_validation_error_message(
                            kit_name=kit_name,
                            hook_id=hook_id,
                            hook_position=idx,
                            total_hooks=len(kit_data["hooks"]),
                            missing_fields=missing_fields,
                            invalid_fields=invalid_fields,
                        )
                        raise click.ClickException(msg) from e

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
                hooks=hooks,
            )

    # Load dev_mode from pyproject.toml if available
    dev_mode = _load_dev_mode_from_pyproject(project_dir)

    return ProjectConfig(
        version=data.get("version", "1"),
        kits=kits,
        dev_mode=dev_mode,
    )


def require_project_config(project_dir: Path) -> ProjectConfig:
    """Load dot-agent.toml and exit with error if not found.

    This is a convenience wrapper around load_project_config that enforces
    the config must exist, displaying a helpful error message if not.

    Returns:
        ProjectConfig if found

    Raises:
        SystemExit: If dot-agent.toml not found
    """
    config = load_project_config(project_dir)
    if config is None:
        msg = "Error: No .agent/dot-agent.toml found. Run 'dot-agent init' to create one."
        user_output(msg)
        raise SystemExit(1)
    return config


def save_project_config(project_dir: Path, config: ProjectConfig) -> None:
    """Save dot-agent.toml to .agent/ directory.

    Always saves to the new location (.agent/dot-agent.toml).
    Creates .agent/ directory if it doesn't exist.
    """
    agent_dir = project_dir / ".agent"
    if not agent_dir.exists():
        agent_dir.mkdir(parents=True)
    config_path = agent_dir / "dot-agent.toml"

    # Convert ProjectConfig to dict
    data = {
        "version": config.version,
        "kits": {},
    }

    for kit_id, kit in config.kits.items():
        kit_data = {
            "kit_id": kit.kit_id,
            "source_type": kit.source_type,
            "version": kit.version,
            "artifacts": kit.artifacts,
        }

        # Add hooks if present
        if kit.hooks:
            kit_data["hooks"] = [h.model_dump(mode="json", exclude_none=True) for h in kit.hooks]

        data["kits"][kit_id] = kit_data

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def create_default_config() -> ProjectConfig:
    """Create default project configuration."""
    return ProjectConfig(
        version="1",
        kits={},
    )
