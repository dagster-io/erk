"""Bundled kit source resolver."""

from pathlib import Path

import erk_kits
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.types import SOURCE_TYPE_BUNDLED
from erk.kits.sources.exceptions import KitManifestError, KitNotFoundError
from erk.kits.sources.resolver import KitSource, ResolvedKit


class BundledKitSource(KitSource):
    """Resolve kits from bundled package data."""

    def can_resolve(self, source: str) -> bool:
        """Check if source is a bundled kit by name."""
        bundled_path = self._get_bundled_kit_path(source)
        if bundled_path is None:
            return False
        manifest_path = bundled_path / "kit.yaml"
        return manifest_path.exists()

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve kit from bundled data by name."""
        bundled_path = self._get_bundled_kit_path(source)
        if bundled_path is None:
            raise KitNotFoundError(source, ["bundled"])

        manifest_path = bundled_path / "kit.yaml"
        if not manifest_path.exists():
            raise KitManifestError(manifest_path)

        manifest = load_kit_manifest(manifest_path)

        # Note: Hyphenated naming (e.g., skills/kit-name-tool/) is the standard
        # convention but not enforced by validation

        # Artifacts are relative to manifest location
        artifacts_base = manifest_path.parent

        return ResolvedKit(
            kit_id=manifest.name,
            version=manifest.version,
            source_type=SOURCE_TYPE_BUNDLED,
            manifest_path=manifest_path,
            artifacts_base=artifacts_base,
        )

    def list_available(self) -> list[str]:
        """List all bundled kit IDs."""
        kits_dir = erk_kits.get_kits_dir()
        if not kits_dir.exists():
            return []

        bundled_kits = []
        for kit_dir in kits_dir.iterdir():
            if kit_dir.is_dir() and (kit_dir / "kit.yaml").exists():
                bundled_kits.append(kit_dir.name)

        return bundled_kits

    def _get_bundled_kit_path(self, source: str) -> Path | None:
        """Get path to bundled kit if it exists."""
        kit_path = erk_kits.get_kits_dir() / source
        if kit_path.exists():
            return kit_path
        return None
