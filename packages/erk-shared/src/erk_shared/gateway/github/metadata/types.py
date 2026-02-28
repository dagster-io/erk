"""Core data structures for GitHub metadata blocks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MetadataBlock:
    """A metadata block with a key and structured YAML data."""

    key: str
    data: dict[str, Any]


@dataclass(frozen=True)
class RawMetadataBlock:
    """A raw metadata block with unparsed body content."""

    key: str
    body: str  # Raw content between HTML comment markers


@dataclass(frozen=True)
class MetadataBlockError:
    """A metadata block that failed to parse."""

    key: str
    message: str


@dataclass(frozen=True)
class MetadataParseResult:
    """Result of parsing metadata blocks, with explicit error reporting."""

    blocks: tuple[MetadataBlock, ...]
    errors: tuple[MetadataBlockError, ...]
    content_blocks: tuple[RawMetadataBlock, ...] = ()

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class MetadataBlockSchema(ABC):
    """Base class for metadata block schemas."""

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> None:
        """Validate data against schema. Raises ValueError if invalid."""
        ...

    @abstractmethod
    def get_key(self) -> str:
        """Return the metadata block key this schema validates."""
        ...
