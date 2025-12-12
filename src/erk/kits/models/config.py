"""Configuration models for erk.kits."""

from dataclasses import dataclass, field, replace

from erk.kits.hooks.models import HookDefinition
from erk.kits.models.types import SourceType


@dataclass(frozen=True)
class InstalledKit:
    """Represents an installed kit in dot-agent.toml."""

    kit_id: str  # Globally unique kit identifier
    source_type: SourceType
    version: str
    artifacts: list[str]
    hooks: list[HookDefinition] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectConfig:
    """Project configuration from dot-agent.toml."""

    version: str
    kits: dict[str, InstalledKit]
    dev_mode: bool = False  # Enable symlink-based kit development

    def update_kit(self, kit: InstalledKit) -> "ProjectConfig":
        """Return new config with updated kit (maintaining immutability)."""
        new_kits = {**self.kits, kit.kit_id: kit}
        return replace(self, kits=new_kits)
