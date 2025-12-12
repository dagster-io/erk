"""Kit source resolution system."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from erk.kits.models.types import SourceType
from erk.kits.sources.exceptions import InvalidKitIdError, ResolverNotConfiguredError

# Kit ID must only contain lowercase letters, numbers, and hyphens
KIT_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")


def validate_kit_id(kit_id: str) -> None:
    """Validate that a kit ID conforms to the allowed format.

    Kit IDs must only contain lowercase letters, numbers, and hyphens.

    Args:
        kit_id: The kit ID to validate

    Raises:
        InvalidKitIdError: If the kit ID contains invalid characters
    """
    if not KIT_ID_PATTERN.match(kit_id):
        raise InvalidKitIdError(kit_id)


@dataclass(frozen=True)
class ResolvedKit:
    """A kit resolved from a source."""

    kit_id: str  # Globally unique kit identifier
    source_type: SourceType
    version: str
    manifest_path: Path
    artifacts_base: Path


class KitSource(ABC):
    """Abstract base class for kit sources."""

    @abstractmethod
    def can_resolve(self, source: str) -> bool:
        """Check if this source can resolve the given kit name."""
        pass

    @abstractmethod
    def resolve(self, source: str) -> ResolvedKit:
        """Resolve a kit from the source by name."""
        pass

    @abstractmethod
    def list_available(self) -> list[str]:
        """List all kit IDs available from this source."""
        pass


class KitResolver:
    """Multi-source kit resolver."""

    def __init__(self, sources: list[KitSource]) -> None:
        self.sources = sources

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve a kit from any available source.

        Raises:
            ResolverNotConfiguredError: If no resolver can handle the source
            KitNotFoundError: If kit not found (should be raised by sources)
            SourceAccessError: If source cannot be accessed (should be raised by sources)
        """
        for resolver_source in self.sources:
            if resolver_source.can_resolve(source):
                return resolver_source.resolve(source)

        # No resolver found - provide detailed error
        available_types = [type(source).__name__ for source in self.sources]
        raise ResolverNotConfiguredError(source, available_types)
