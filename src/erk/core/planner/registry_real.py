"""Real implementation of PlannerRegistry using TOML file storage.

Stores planner configuration in ~/.erk/planners.toml.
"""

import tomllib
from datetime import datetime
from pathlib import Path

import tomlkit

from erk.core.planner.registry_abc import PlannerRegistry
from erk.core.planner.types import RegisteredPlanner

SCHEMA_VERSION = 1


class RealPlannerRegistry(PlannerRegistry):
    """Production implementation that reads/writes ~/.erk/planners.toml."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the registry.

        Args:
            config_path: Optional custom path for the config file.
                        Defaults to ~/.erk/planners.toml
        """
        self._config_path = config_path or (Path.home() / ".erk" / "planners.toml")

    def _load_data(self) -> dict:
        """Load data from TOML file.

        Returns:
            Parsed TOML data, or empty structure if file doesn't exist
        """
        if not self._config_path.exists():
            return {"schema_version": SCHEMA_VERSION, "planners": {}}

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

        if "default_planner" in data and data["default_planner"] is not None:
            doc["default_planner"] = data["default_planner"]

        # Add planners table
        planners_table = tomlkit.table()
        for name, planner_data in data.get("planners", {}).items():
            planner_table = tomlkit.table()
            planner_table["gh_name"] = planner_data["gh_name"]
            planner_table["repository"] = planner_data["repository"]
            planner_table["configured"] = planner_data["configured"]
            planner_table["registered_at"] = planner_data["registered_at"]
            if planner_data.get("last_connected_at") is not None:
                planner_table["last_connected_at"] = planner_data["last_connected_at"]
            planners_table[name] = planner_table

        doc["planners"] = planners_table

        self._config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def _planner_from_dict(self, name: str, data: dict) -> RegisteredPlanner:
        """Convert a dict to a RegisteredPlanner.

        Args:
            name: Planner name
            data: Dict with planner data

        Returns:
            RegisteredPlanner instance
        """
        return RegisteredPlanner(
            name=name,
            gh_name=data["gh_name"],
            repository=data["repository"],
            configured=data["configured"],
            registered_at=datetime.fromisoformat(data["registered_at"]),
            last_connected_at=(
                datetime.fromisoformat(data["last_connected_at"])
                if data.get("last_connected_at")
                else None
            ),
        )

    def _planner_to_dict(self, planner: RegisteredPlanner) -> dict:
        """Convert a RegisteredPlanner to a dict.

        Args:
            planner: RegisteredPlanner instance

        Returns:
            Dict representation
        """
        result = {
            "gh_name": planner.gh_name,
            "repository": planner.repository,
            "configured": planner.configured,
            "registered_at": planner.registered_at.isoformat(),
        }
        if planner.last_connected_at is not None:
            result["last_connected_at"] = planner.last_connected_at.isoformat()
        return result

    def list_planners(self) -> list[RegisteredPlanner]:
        """List all registered planners."""
        data = self._load_data()
        planners = data.get("planners", {})
        return [self._planner_from_dict(name, pdata) for name, pdata in planners.items()]

    def get(self, name: str) -> RegisteredPlanner | None:
        """Get a planner by name."""
        data = self._load_data()
        planners = data.get("planners", {})
        if name not in planners:
            return None
        return self._planner_from_dict(name, planners[name])

    def get_default(self) -> RegisteredPlanner | None:
        """Get the default planner."""
        data = self._load_data()
        default_name = data.get("default_planner")
        if default_name is None:
            return None
        return self.get(default_name)

    def get_default_name(self) -> str | None:
        """Get the name of the default planner."""
        data = self._load_data()
        return data.get("default_planner")

    def set_default(self, name: str) -> None:
        """Set the default planner."""
        data = self._load_data()
        planners = data.get("planners", {})
        if name not in planners:
            raise ValueError(f"No planner named '{name}' exists")
        data["default_planner"] = name
        self._save_data(data)

    def register(self, planner: RegisteredPlanner) -> None:
        """Register a new planner."""
        data = self._load_data()
        planners = data.get("planners", {})
        if planner.name in planners:
            raise ValueError(f"Planner '{planner.name}' already exists")
        planners[planner.name] = self._planner_to_dict(planner)
        data["planners"] = planners
        self._save_data(data)

    def unregister(self, name: str) -> None:
        """Remove a planner from the registry."""
        data = self._load_data()
        planners = data.get("planners", {})
        if name not in planners:
            raise ValueError(f"No planner named '{name}' exists")
        del planners[name]
        data["planners"] = planners

        # Clear default if we're removing the default planner
        if data.get("default_planner") == name:
            data["default_planner"] = None

        self._save_data(data)

    def mark_configured(self, name: str) -> None:
        """Mark a planner as configured."""
        data = self._load_data()
        planners = data.get("planners", {})
        if name not in planners:
            raise ValueError(f"No planner named '{name}' exists")
        planners[name]["configured"] = True
        data["planners"] = planners
        self._save_data(data)

    def update_last_connected(self, name: str, timestamp: datetime) -> None:
        """Update the last connected timestamp for a planner."""
        data = self._load_data()
        planners = data.get("planners", {})
        if name not in planners:
            raise ValueError(f"No planner named '{name}' exists")
        planners[name]["last_connected_at"] = timestamp.isoformat()
        data["planners"] = planners
        self._save_data(data)
