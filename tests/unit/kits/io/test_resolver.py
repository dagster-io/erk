"""Tests for kit source resolution."""

from pathlib import Path
from typing import cast

import pytest

from erk.kits.models.types import SourceType
from erk.kits.sources.exceptions import (
    KitManifestError,
    KitNotFoundError,
    ResolverNotConfiguredError,
)
from erk.kits.sources.resolver import KitResolver, ResolvedKit
from erk.kits.sources.standalone import StandalonePackageSource


def test_standalone_can_resolve() -> None:
    """Test package detection."""
    source = StandalonePackageSource()
    assert source.can_resolve("click") is True
    assert source.can_resolve("nonexistent_package") is False


def test_standalone_resolve_not_installed() -> None:
    """Test resolving non-existent package."""
    source = StandalonePackageSource()

    with pytest.raises(KitNotFoundError, match="not found"):
        source.resolve("nonexistent_package")


def test_standalone_resolve_no_manifest(tmp_path: Path) -> None:
    """Test resolving package without kit.yaml."""
    # We can't easily test this without mocking since it requires
    # a real package without kit.yaml. This test validates the error path.
    source = StandalonePackageSource()

    # click doesn't have kit.yaml, so this should fail
    with pytest.raises(KitManifestError):
        source.resolve("click")


def test_kit_resolver_resolve_from_package(tmp_path: Path) -> None:
    """Test resolving kit from package using mock."""
    # Create a mock kit structure
    kit_dir = tmp_path / "mock_kit"
    kit_dir.mkdir()

    manifest_path = kit_dir / "kit.yaml"
    manifest_path.write_text(
        "name: test-kit\nversion: 1.0.0\ndescription: Test kit\n"
        "artifacts:\n  agent:\n    - agents/test.md\n",
        encoding="utf-8",
    )

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test.md").write_text("# Test Agent", encoding="utf-8")

    # Create a custom source for testing
    class MockSource(StandalonePackageSource):
        def can_resolve(self, source: str) -> bool:
            return source == "test-kit"

        def resolve(self, source: str) -> ResolvedKit:
            if source != "test-kit":
                raise ValueError(f"Cannot resolve: {source}")

            return ResolvedKit(
                kit_id="test-kit",
                version="1.0.0",
                source_type="package",
                manifest_path=manifest_path,
                artifacts_base=kit_dir,
            )

    resolver = KitResolver(sources=[MockSource()])
    resolved = resolver.resolve("test-kit")

    assert resolved.kit_id == "test-kit"
    assert resolved.source_type == "package"
    assert resolved.manifest_path == manifest_path
    assert resolved.artifacts_base == kit_dir


def test_kit_resolver_no_source_found() -> None:
    """Test resolver with no matching source."""
    resolver = KitResolver(sources=[])

    with pytest.raises(ResolverNotConfiguredError, match="No resolver configured"):
        resolver.resolve("anything")


def test_kit_resolver_multiple_sources(tmp_path: Path) -> None:
    """Test resolver tries sources in order."""

    # Create two mock sources
    class FirstSource(StandalonePackageSource):
        def can_resolve(self, source: str) -> bool:
            return source == "first-kit"

        def resolve(self, source: str) -> ResolvedKit:
            return ResolvedKit(
                kit_id="first-kit",
                version="1.0.0",
                source_type=cast(SourceType, "first"),
                manifest_path=tmp_path / "first.yaml",
                artifacts_base=tmp_path,
            )

    class SecondSource(StandalonePackageSource):
        def can_resolve(self, source: str) -> bool:
            return source == "second-kit"

        def resolve(self, source: str) -> ResolvedKit:
            return ResolvedKit(
                kit_id="second-kit",
                version="1.0.0",
                source_type=cast(SourceType, "second"),
                manifest_path=tmp_path / "second.yaml",
                artifacts_base=tmp_path,
            )

    resolver = KitResolver(sources=[FirstSource(), SecondSource()])

    # Test first source
    resolved = resolver.resolve("first-kit")
    assert resolved.kit_id == "first-kit"
    assert resolved.source_type == "first"

    # Test second source
    resolved = resolver.resolve("second-kit")
    assert resolved.kit_id == "second-kit"
    assert resolved.source_type == "second"

    # Test no matching source
    with pytest.raises(ResolverNotConfiguredError, match="No resolver configured"):
        resolver.resolve("unknown-kit")


def test_resolved_kit_immutable() -> None:
    """Test ResolvedKit is frozen (immutable)."""
    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=Path("/tmp/kit.yaml"),
        artifacts_base=Path("/tmp"),
    )

    with pytest.raises(AttributeError):
        resolved.kit_id = "other-kit"  # type: ignore
