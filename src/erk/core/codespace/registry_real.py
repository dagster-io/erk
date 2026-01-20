"""Real implementation of CodespaceRegistry using TOML file storage.

Stores codespace configuration in ~/.erk/codespaces.toml.

The registry class is immutable - mutation operations are standalone functions
that save to disk and return a new registry instance.
"""

import tomllib
from datetime import datetime
from pathlib import Path

import tomlkit

from erk.core.codespace.registry_abc import CodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace

SCHEMA_VERSION = 1


def _load_toml_data(config_path: Path) -> dict:
    """Load data from TOML file.

    Args:
        config_path: Path to the config file

    Returns:
        Parsed TOML data, or empty structure if file doesn't exist
    """
    if not config_path.exists():
        return {"schema_version": SCHEMA_VERSION, "codespaces": {}}

    content = config_path.read_text(encoding="utf-8")
    return tomllib.loads(content)


def _save_toml_data(config_path: Path, data: dict) -> None:
    """Save data to TOML file.

    Args:
        config_path: Path to the config file
        data: Data structure to save
    """
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Use tomlkit to preserve formatting
    doc = tomlkit.document()
    doc["schema_version"] = data.get("schema_version", SCHEMA_VERSION)

    if "default_codespace" in data and data["default_codespace"] is not None:
        doc["default_codespace"] = data["default_codespace"]

    # Add codespaces table
    codespaces_table = tomlkit.table()
    for name, codespace_data in data.get("codespaces", {}).items():
        codespace_table = tomlkit.table()
        codespace_table["gh_name"] = codespace_data["gh_name"]
        codespace_table["created_at"] = codespace_data["created_at"]
        codespaces_table[name] = codespace_table

    doc["codespaces"] = codespaces_table

    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def _codespace_from_dict(name: str, data: dict) -> RegisteredCodespace:
    """Convert a dict to a RegisteredCodespace.

    Args:
        name: Codespace name
        data: Dict with codespace data

    Returns:
        RegisteredCodespace instance
    """
    return RegisteredCodespace(
        name=name,
        gh_name=data["gh_name"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _codespace_to_dict(codespace: RegisteredCodespace) -> dict:
    """Convert a RegisteredCodespace to a dict.

    Args:
        codespace: RegisteredCodespace instance

    Returns:
        Dict representation
    """
    return {
        "gh_name": codespace.gh_name,
        "created_at": codespace.created_at.isoformat(),
    }


class RealCodespaceRegistry(CodespaceRegistry):
    """Production implementation that stores codespace data immutably.

    This class receives fully loaded data at construction time and provides
    read-only access. Mutation operations are standalone functions that
    save to disk and return new registry instances.
    """

    def __init__(
        self,
        *,
        config_path: Path,
        codespaces: dict[str, RegisteredCodespace],
        default_codespace: str | None,
    ) -> None:
        """Initialize the registry with loaded data.

        Args:
            config_path: Path to the codespaces.toml config file.
            codespaces: Dict mapping names to RegisteredCodespace instances.
            default_codespace: Name of the default codespace, or None.
        """
        self._config_path = config_path
        self._codespaces = codespaces
        self._default_codespace = default_codespace

    @staticmethod
    def from_config_path(config_path: Path) -> "RealCodespaceRegistry":
        """Create a registry by loading data from a TOML config file.

        Args:
            config_path: Path to the codespaces.toml config file.
                        Typically obtained from erk_installation.get_codespaces_config_path().

        Returns:
            RealCodespaceRegistry with loaded data.
        """
        data = _load_toml_data(config_path)
        codespaces_data = data.get("codespaces", {})
        codespaces = {
            name: _codespace_from_dict(name, cdata) for name, cdata in codespaces_data.items()
        }
        default_codespace = data.get("default_codespace")
        return RealCodespaceRegistry(
            config_path=config_path,
            codespaces=codespaces,
            default_codespace=default_codespace,
        )

    @property
    def config_path(self) -> Path:
        """The path to the config file."""
        return self._config_path

    def list_codespaces(self) -> list[RegisteredCodespace]:
        """List all registered codespaces."""
        return list(self._codespaces.values())

    def get(self, name: str) -> RegisteredCodespace | None:
        """Get a codespace by name."""
        return self._codespaces.get(name)

    def get_default(self) -> RegisteredCodespace | None:
        """Get the default codespace."""
        if self._default_codespace is None:
            return None
        return self._codespaces.get(self._default_codespace)

    def get_default_name(self) -> str | None:
        """Get the name of the default codespace."""
        return self._default_codespace


# Standalone mutation functions that save to disk and return new registry


def register_codespace(
    config_path: Path,
    codespace: RegisteredCodespace,
) -> RealCodespaceRegistry:
    """Register a new codespace and return a new registry with updated state.

    Args:
        config_path: Path to the codespaces.toml config file.
        codespace: The codespace to register.

    Returns:
        New RealCodespaceRegistry with the codespace added.

    Raises:
        ValueError: If a codespace with that name already exists.
    """
    data = _load_toml_data(config_path)
    codespaces = data.get("codespaces", {})
    if codespace.name in codespaces:
        raise ValueError(f"Codespace '{codespace.name}' already exists")
    codespaces[codespace.name] = _codespace_to_dict(codespace)
    data["codespaces"] = codespaces
    _save_toml_data(config_path, data)
    return RealCodespaceRegistry.from_config_path(config_path)


def unregister_codespace(
    config_path: Path,
    name: str,
) -> RealCodespaceRegistry:
    """Unregister a codespace and return a new registry with updated state.

    Args:
        config_path: Path to the codespaces.toml config file.
        name: Name of the codespace to remove.

    Returns:
        New RealCodespaceRegistry with the codespace removed.

    Raises:
        ValueError: If no codespace with that name exists.
    """
    data = _load_toml_data(config_path)
    codespaces = data.get("codespaces", {})
    if name not in codespaces:
        raise ValueError(f"No codespace named '{name}' exists")
    del codespaces[name]
    data["codespaces"] = codespaces

    # Clear default if we're removing the default codespace
    if data.get("default_codespace") == name:
        data["default_codespace"] = None

    _save_toml_data(config_path, data)
    return RealCodespaceRegistry.from_config_path(config_path)


def set_default_codespace(
    config_path: Path,
    name: str,
) -> RealCodespaceRegistry:
    """Set the default codespace and return a new registry with updated state.

    Args:
        config_path: Path to the codespaces.toml config file.
        name: Name of the codespace to set as default.

    Returns:
        New RealCodespaceRegistry with the default updated.

    Raises:
        ValueError: If no codespace with that name exists.
    """
    data = _load_toml_data(config_path)
    codespaces = data.get("codespaces", {})
    if name not in codespaces:
        raise ValueError(f"No codespace named '{name}' exists")
    data["default_codespace"] = name
    _save_toml_data(config_path, data)
    return RealCodespaceRegistry.from_config_path(config_path)
