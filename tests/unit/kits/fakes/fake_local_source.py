"""Fake local path source for testing."""

from pathlib import Path
from typing import cast

from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.types import SourceType
from erk.kits.sources.resolver import KitSource, ResolvedKit


class FakeLocalSource(KitSource):
    """Resolve kits from local filesystem paths (for testing only)."""

    def can_resolve(self, source: str) -> bool:
        """Check if source is a local path with kit.yaml."""
        path = Path(source)
        if not path.exists():
            return False
        if not path.is_dir():
            return False
        manifest_path = path / "kit.yaml"
        return manifest_path.exists()

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve kit from local filesystem path."""
        path = Path(source).resolve()

        if not path.exists():
            raise ValueError(f"Path does not exist: {source}")

        if not path.is_dir():
            raise ValueError(f"Not a directory: {source}")

        manifest_path = path / "kit.yaml"
        if not manifest_path.exists():
            raise ValueError(f"No kit.yaml found in: {source}")

        manifest = load_kit_manifest(manifest_path)

        return ResolvedKit(
            kit_id=manifest.name,
            version=manifest.version,
            source_type=cast(SourceType, "local"),
            manifest_path=manifest_path,
            artifacts_base=path,
        )

    def list_available(self) -> list[str]:
        """List available kits (not applicable for local paths)."""
        return []
