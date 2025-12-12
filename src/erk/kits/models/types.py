"""Common type definitions for erk.kits."""

from typing import Literal

# Source type for kits - either bundled with dot-agent or standalone packages
SourceType = Literal["bundled", "package"]

# Constants for source types to avoid magic strings
SOURCE_TYPE_BUNDLED: SourceType = "bundled"
SOURCE_TYPE_PACKAGE: SourceType = "package"
