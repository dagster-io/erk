"""Standalone package source resolver."""

from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.types import SOURCE_TYPE_PACKAGE
from erk.kits.sources.exceptions import KitManifestError, KitNotFoundError, SourceAccessError
from erk.kits.sources.resolver import KitSource, ResolvedKit
from erk.kits.utils.packaging import find_kit_manifest, get_package_path, is_package_installed


class StandalonePackageSource(KitSource):
    """Resolve kits from standalone Python packages."""

    def can_resolve(self, source: str) -> bool:
        """Check if source is an installed Python package by name."""
        # Try to resolve as a package if not a bundled kit
        return is_package_installed(source)

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve kit from Python package by name."""
        if not is_package_installed(source):
            raise KitNotFoundError(source, ["package"])

        package_path = get_package_path(source)
        if package_path is None:
            raise SourceAccessError("package", source)

        manifest_path = find_kit_manifest(package_path)
        if manifest_path is None:
            raise KitManifestError(package_path / "kit.yaml")

        manifest = load_kit_manifest(manifest_path)

        # Artifacts are relative to manifest location
        artifacts_base = manifest_path.parent

        return ResolvedKit(
            kit_id=manifest.name,
            version=manifest.version,
            source_type=SOURCE_TYPE_PACKAGE,
            manifest_path=manifest_path,
            artifacts_base=artifacts_base,
        )

    def list_available(self) -> list[str]:
        """List available kits from standalone packages.

        For standalone packages, we cannot enumerate all installed packages
        that might be kits, so we return an empty list. Users must explicitly
        specify package names to install.
        """
        return []
