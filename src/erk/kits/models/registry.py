"""Registry models."""

from dataclasses import dataclass

from erk.kits.models.types import SourceType


@dataclass(frozen=True)
class RegistryEntry:
    """Kit entry in the registry."""

    kit_id: str  # Globally unique kit identifier
    source_type: SourceType
    description: str
    version: str
