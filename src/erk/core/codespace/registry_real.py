"""Real implementation of CodespaceRegistry using TOML file storage.

Stores codespace configuration in ~/.erk/codespaces.toml.
"""

import tomllib
from datetime import datetime
from pathlib import Path

import tomlkit

from erk.core.codespace.registry_abc import CodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace

SCHEMA_VERSION = 1


class RealCodespaceRegistry(CodespaceRegistry):
    """Production implementation that reads/writes ~/.erk/codespaces.toml."""

    def __init__(self, config_path: Path) -> None:
        """Initialize the registry.

        Args:
            config_path: Path to the codespaces.toml config file.
                        Typically obtained from erk_installation.get_codespaces_config_path().
        """
        self._config_path = config_path

    def _load_data(self) -> dict:
        """Load data from TOML file.

        Returns:
            Parsed TOML data, or empty structure if file doesn't exist
        """
        if not self._config_path.exists():
            return {"schema_version": SCHEMA_VERSION, "codespaces": {}}

        content = self._config_path.read_text(encoding="utf-8")
        return tomllib.loads(content)

    def _save_data(self, data: dict) -> None:
        """Save data to TOML file.

        Args:
            data: Data structure to save
        """
        # Ensure parent directory exists
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

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

        self._config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def _codespace_from_dict(self, name: str, data: dict) -> RegisteredCodespace:
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

    def _codespace_to_dict(self, codespace: RegisteredCodespace) -> dict:
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

    def list_codespaces(self) -> list[RegisteredCodespace]:
        """List all registered codespaces."""
        data = self._load_data()
        codespaces = data.get("codespaces", {})
        return [self._codespace_from_dict(name, cdata) for name, cdata in codespaces.items()]

    def get(self, name: str) -> RegisteredCodespace | None:
        """Get a codespace by name."""
        data = self._load_data()
        codespaces = data.get("codespaces", {})
        if name not in codespaces:
            return None
        return self._codespace_from_dict(name, codespaces[name])

    def get_default(self) -> RegisteredCodespace | None:
        """Get the default codespace."""
        data = self._load_data()
        default_name = data.get("default_codespace")
        if default_name is None:
            return None
        return self.get(default_name)

    def get_default_name(self) -> str | None:
        """Get the name of the default codespace."""
        data = self._load_data()
        return data.get("default_codespace")

    def set_default(self, name: str) -> None:
        """Set the default codespace."""
        data = self._load_data()
        codespaces = data.get("codespaces", {})
        if name not in codespaces:
            raise ValueError(f"No codespace named '{name}' exists")
        data["default_codespace"] = name
        self._save_data(data)

    def register(self, codespace: RegisteredCodespace) -> None:
        """Register a new codespace."""
        data = self._load_data()
        codespaces = data.get("codespaces", {})
        if codespace.name in codespaces:
            raise ValueError(f"Codespace '{codespace.name}' already exists")
        codespaces[codespace.name] = self._codespace_to_dict(codespace)
        data["codespaces"] = codespaces
        self._save_data(data)

    def unregister(self, name: str) -> None:
        """Remove a codespace from the registry."""
        data = self._load_data()
        codespaces = data.get("codespaces", {})
        if name not in codespaces:
            raise ValueError(f"No codespace named '{name}' exists")
        del codespaces[name]
        data["codespaces"] = codespaces

        # Clear default if we're removing the default codespace
        if data.get("default_codespace") == name:
            data["default_codespace"] = None

        self._save_data(data)
