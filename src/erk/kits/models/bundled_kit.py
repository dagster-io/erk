"""Models for bundled kit information.

Bundled kits provide docs that are NOT installed as artifacts,
but are available directly from the kit's source directory.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BundledKitInfo:
    """Information about a bundled kit's available items.

    Represents items from bundled kits that are NOT installed as artifacts but are
    still available for use (docs can be viewed/installed).
    """

    kit_id: str
    version: str
    available_docs: list[str]  # Doc paths relative to kit (e.g., "tools/gt.md")
    level: str  # "user" or "project"
