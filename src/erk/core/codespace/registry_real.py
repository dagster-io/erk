"""Production implementation of CodespaceRegistry using filesystem."""

import tomllib
from datetime import datetime
from pathlib import Path

import tomlkit

from erk.core.codespace.registry_abc import CodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace

# Schema version for future migrations
SCHEMA_VERSION = 1


class RealCodespaceRegistry(CodespaceRegistry):
    """Production implementation that reads/writes ~/.erk/codespaces.toml."""

    def exists(self) -> bool:
        """Check if registry file exists."""
        return self.path().exists()

    def list_codespaces(self) -> list[RegisteredCodespace]:
        """List all registered codespaces, sorted by last_connected_at desc."""
        if not self.exists():
            return []

        codespaces = list(self._load().values())

        # Sort: most recently connected first, never-connected at end
        # Use tuple: (has_connected, last_connected_at)
        # - has_connected: 1 for connected (sorts first), 0 for never (sorts last)
        # - last_connected_at: actual datetime for sorting within connected group
        def sort_key(cs: RegisteredCodespace) -> tuple[int, datetime]:
            if cs.last_connected_at is None:
                return (0, datetime.min)  # Never connected goes last
            return (1, cs.last_connected_at)  # Connected goes first, sorted by date

        return sorted(codespaces, key=sort_key, reverse=True)

    def get(self, friendly_name: str) -> RegisteredCodespace | None:
        """Get codespace by friendly name."""
        if not self.exists():
            return None
        return self._load().get(friendly_name)

    def register(self, codespace: RegisteredCodespace) -> None:
        """Register a new codespace."""
        data = self._load() if self.exists() else {}

        if codespace.friendly_name in data:
            raise ValueError(f"Codespace '{codespace.friendly_name}' already exists")

        data[codespace.friendly_name] = codespace
        self._save(data)

    def update(self, codespace: RegisteredCodespace) -> None:
        """Update an existing codespace."""
        if not self.exists():
            raise KeyError(f"Codespace '{codespace.friendly_name}' not found")

        data = self._load()
        if codespace.friendly_name not in data:
            raise KeyError(f"Codespace '{codespace.friendly_name}' not found")

        data[codespace.friendly_name] = codespace
        self._save(data)

    def unregister(self, friendly_name: str) -> None:
        """Remove codespace from registry."""
        if not self.exists():
            raise KeyError(f"Codespace '{friendly_name}' not found")

        data = self._load()
        if friendly_name not in data:
            raise KeyError(f"Codespace '{friendly_name}' not found")

        del data[friendly_name]
        self._save(data)

    def update_last_connected(self, friendly_name: str, timestamp: datetime) -> None:
        """Update last_connected_at timestamp."""
        codespace = self.get(friendly_name)
        if codespace is None:
            raise KeyError(f"Codespace '{friendly_name}' not found")

        updated = RegisteredCodespace(
            friendly_name=codespace.friendly_name,
            gh_name=codespace.gh_name,
            repository=codespace.repository,
            branch=codespace.branch,
            machine_type=codespace.machine_type,
            configured=codespace.configured,
            registered_at=codespace.registered_at,
            last_connected_at=timestamp,
            notes=codespace.notes,
        )
        self.update(updated)

    def mark_configured(self, friendly_name: str) -> None:
        """Mark codespace as configured."""
        codespace = self.get(friendly_name)
        if codespace is None:
            raise KeyError(f"Codespace '{friendly_name}' not found")

        updated = RegisteredCodespace(
            friendly_name=codespace.friendly_name,
            gh_name=codespace.gh_name,
            repository=codespace.repository,
            branch=codespace.branch,
            machine_type=codespace.machine_type,
            configured=True,
            registered_at=codespace.registered_at,
            last_connected_at=codespace.last_connected_at,
            notes=codespace.notes,
        )
        self.update(updated)

    def path(self) -> Path:
        """Get path to registry file."""
        return Path.home() / ".erk" / "codespaces.toml"

    def _load(self) -> dict[str, RegisteredCodespace]:
        """Load and parse registry from TOML."""
        registry_path = self.path()
        if not registry_path.exists():
            return {}

        content = registry_path.read_text(encoding="utf-8")
        data = tomllib.loads(content)

        # Check schema version
        schema_version = data.get("schema_version", 1)
        if schema_version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Registry file uses schema version {schema_version}, "
                f"but this version of erk only supports up to version {SCHEMA_VERSION}.\n\n"
                f"Please upgrade erk: pip install --upgrade erk"
            )

        codespaces: dict[str, RegisteredCodespace] = {}
        for name, info in data.get("codespaces", {}).items():
            codespaces[name] = RegisteredCodespace(
                friendly_name=name,
                gh_name=info["gh_name"],
                repository=info["repository"],
                branch=info["branch"],
                machine_type=info.get("machine_type", "standardLinux32gb"),
                configured=info.get("configured", False),
                registered_at=datetime.fromisoformat(info["registered_at"]),
                last_connected_at=(
                    datetime.fromisoformat(info["last_connected_at"])
                    if info.get("last_connected_at")
                    else None
                ),
                notes=info.get("notes"),
            )

        return codespaces

    def _save(self, data: dict[str, RegisteredCodespace]) -> None:
        """Save registry to TOML."""
        registry_path = self.path()
        parent = registry_path.parent

        # Ensure parent directory exists
        parent.mkdir(parents=True, exist_ok=True)

        # Build TOML document
        doc = tomlkit.document()
        doc["schema_version"] = SCHEMA_VERSION

        codespaces_table = tomlkit.table()
        for name, cs in sorted(data.items()):
            entry = tomlkit.table()
            entry["gh_name"] = cs.gh_name
            entry["repository"] = cs.repository
            entry["branch"] = cs.branch
            entry["machine_type"] = cs.machine_type
            entry["configured"] = cs.configured
            entry["registered_at"] = cs.registered_at.isoformat()
            if cs.last_connected_at:
                entry["last_connected_at"] = cs.last_connected_at.isoformat()
            if cs.notes:
                entry["notes"] = cs.notes
            codespaces_table[name] = entry

        doc["codespaces"] = codespaces_table

        registry_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
