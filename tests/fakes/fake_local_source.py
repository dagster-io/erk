"""Fake implementation of KitSource for testing local kit directories."""

from pathlib import Path

from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.types import SOURCE_TYPE_PACKAGE
from erk.kits.sources.exceptions import KitManifestError, KitNotFoundError
from erk.kits.sources.resolver import KitSource, ResolvedKit


class FakeLocalSource(KitSource):
    """Fake kit source that resolves kits from local directories.

    This implementation allows tests to create temporary kit directories
    and have them resolved by the kit resolution system.
    """

    def can_resolve(self, source: str) -> bool:
        """Check if source is a local directory path with kit.yaml.

        Args:
            source: Kit source identifier (could be path)

        Returns:
            True if source is a local path containing kit.yaml
        """
        path = Path(source)
        if path.exists() and path.is_dir():
            manifest_path = path / "kit.yaml"
            return manifest_path.exists()
        return False

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve kit from local directory path.

        Args:
            source: Path to local kit directory

        Returns:
            ResolvedKit with manifest info

        Raises:
            KitNotFoundError: If path doesn't exist or is not a directory
            KitManifestError: If kit.yaml not found or invalid
        """
        path = Path(source)
        if not path.exists() or not path.is_dir():
            raise KitNotFoundError(source, ["local"])

        manifest_path = path / "kit.yaml"
        if not manifest_path.exists():
            raise KitManifestError(manifest_path)

        manifest = load_kit_manifest(manifest_path)

        return ResolvedKit(
            kit_id=manifest.name,
            version=manifest.version,
            source_type=SOURCE_TYPE_PACKAGE,
            manifest_path=manifest_path,
            artifacts_base=path,
        )

    def list_available(self) -> list[str]:
        """List available kits from local source.

        For local directories, we cannot enumerate available kits,
        so we return an empty list.

        Returns:
            Empty list (local source doesn't support enumeration)
        """
        return []
