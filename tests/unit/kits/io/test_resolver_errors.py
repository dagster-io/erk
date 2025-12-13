"""Tests for resolver error handling with specific exceptions."""

import tempfile
from pathlib import Path
from typing import cast

import pytest

from erk.cli.commands.kit.install import check_for_updates
from erk.kits.models.config import InstalledKit
from erk.kits.models.types import SourceType
from erk.kits.sources.exceptions import (
    KitManifestError,
    KitNotFoundError,
    KitResolutionError,
    KitVersionError,
    ResolverNotConfiguredError,
    SourceAccessError,
)
from erk.kits.sources.resolver import KitResolver, KitSource, ResolvedKit


class MockKitSource(KitSource):
    """Mock kit source for testing."""

    def __init__(self, can_resolve_result: bool = True, resolve_exception: Exception | None = None):
        self.can_resolve_result = can_resolve_result
        self.resolve_exception = resolve_exception
        self.resolved_kit = ResolvedKit(
            kit_id="test-kit",
            version="1.0.0",
            source_type=cast(SourceType, "mock"),
            manifest_path=Path("/tmp/manifest.yaml"),
            artifacts_base=Path("/tmp/artifacts"),
        )

    def can_resolve(self, source: str) -> bool:
        return self.can_resolve_result

    def resolve(self, source: str) -> ResolvedKit:
        if self.resolve_exception:
            raise self.resolve_exception
        return self.resolved_kit

    def list_available(self) -> list[str]:
        return ["test-kit"]


def test_resolver_not_configured_error():
    """Test ResolverNotConfiguredError is raised when no resolver can handle source."""
    # Create resolver with sources that can't resolve the requested kit
    source1 = MockKitSource(can_resolve_result=False)
    source2 = MockKitSource(can_resolve_result=False)
    resolver = KitResolver(sources=[source1, source2])

    with pytest.raises(ResolverNotConfiguredError) as exc_info:
        resolver.resolve("unknown-source")

    error = exc_info.value
    assert error.source == "unknown-source"
    assert "MockKitSource" in error.available_types[0]
    assert "No resolver configured for source 'unknown-source'" in str(error)


def test_kit_not_found_error():
    """Test KitNotFoundError propagates from source."""
    # Create source that raises KitNotFoundError
    exception = KitNotFoundError("test-kit", ["bundled", "package"])
    source = MockKitSource(resolve_exception=exception)
    resolver = KitResolver(sources=[source])

    with pytest.raises(KitNotFoundError) as exc_info:
        resolver.resolve("test-kit")

    error = exc_info.value
    assert error.kit_id == "test-kit"
    assert error.sources_checked == ["bundled", "package"]
    assert "Kit 'test-kit' not found" in str(error)


def test_source_access_error():
    """Test SourceAccessError propagates from source."""
    # Create source that raises SourceAccessError
    cause = OSError("Network unreachable")
    exception = SourceAccessError("remote", "https://example.com/kit", cause)
    source = MockKitSource(resolve_exception=exception)
    resolver = KitResolver(sources=[source])

    with pytest.raises(SourceAccessError) as exc_info:
        resolver.resolve("remote-kit")

    error = exc_info.value
    assert error.source_type == "remote"
    assert error.source == "https://example.com/kit"
    assert error.cause is cause
    assert "Failed to access remote source" in str(error)
    assert "Network unreachable" in str(error)


def test_kit_manifest_error():
    """Test KitManifestError for manifest loading issues."""
    manifest_path = Path("/tmp/bad-manifest.yaml")
    cause = ValueError("Invalid YAML")
    exception = KitManifestError(manifest_path, cause)

    assert exception.manifest_path == manifest_path
    assert exception.cause is cause
    assert "Failed to load kit manifest" in str(exception)
    assert "Invalid YAML" in str(exception)


def test_kit_version_error():
    """Test KitVersionError for version-related issues."""
    exception = KitVersionError("test-kit", "Version 2.0.0 requires Python 3.12+")

    assert exception.kit_id == "test-kit"
    assert "Version error for kit 'test-kit'" in str(exception)
    assert "requires Python 3.12+" in str(exception)


def test_check_for_updates_with_kit_not_found_error():
    """Test check_for_updates handles KitNotFoundError gracefully."""
    installed = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=[],
        hooks=[],
    )

    # Create resolver that raises KitNotFoundError
    exception = KitNotFoundError("test-kit", ["bundled"])
    source = MockKitSource(resolve_exception=exception)
    resolver = KitResolver(sources=[source])

    has_update, resolved, error_msg = check_for_updates(installed, resolver)

    assert has_update is False
    assert resolved is None
    assert error_msg is not None
    assert "Kit no longer available" in error_msg


def test_check_for_updates_with_resolver_not_configured_error():
    """Test check_for_updates handles ResolverNotConfiguredError gracefully."""
    installed = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=[],
        hooks=[],
    )

    # Create resolver with no matching sources
    source = MockKitSource(can_resolve_result=False)
    resolver = KitResolver(sources=[source])

    has_update, resolved, error_msg = check_for_updates(installed, resolver)

    assert has_update is False
    assert resolved is None
    assert error_msg is not None
    assert "Resolver configuration changed" in error_msg


def test_check_for_updates_with_source_access_error():
    """Test check_for_updates handles SourceAccessError gracefully."""
    installed = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=[],
        hooks=[],
    )

    # Create resolver that raises SourceAccessError
    exception = SourceAccessError("remote", "https://example.com", OSError("Timeout"))
    source = MockKitSource(resolve_exception=exception)
    resolver = KitResolver(sources=[source])

    has_update, resolved, error_msg = check_for_updates(installed, resolver)

    assert has_update is False
    assert resolved is None
    assert error_msg is not None
    assert "Source access failed" in error_msg


def test_check_for_updates_with_generic_resolution_error():
    """Test check_for_updates handles generic KitResolutionError gracefully."""
    installed = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=[],
        hooks=[],
    )

    # Create resolver that raises generic KitResolutionError
    exception = KitResolutionError("Something went wrong")
    source = MockKitSource(resolve_exception=exception)
    resolver = KitResolver(sources=[source])

    has_update, resolved, error_msg = check_for_updates(installed, resolver)

    assert has_update is False
    assert resolved is None
    assert error_msg is not None
    assert "Resolution error" in error_msg
    assert "Something went wrong" in error_msg


def test_check_for_updates_success_with_update_available():
    """Test check_for_updates succeeds when update is available."""
    installed = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=[],
        hooks=[],
    )

    # Create mock manifest with newer version
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_path = Path(temp_dir) / "manifest.yaml"
        manifest_path.write_text("""
name: test-kit
version: "2.0.0"
description: Test kit
artifacts:
  agent: []
""")

        # Create source that returns resolved kit
        source = MockKitSource()
        source.resolved_kit = ResolvedKit(
            kit_id="test-kit",
            version="2.0.0",
            source_type=cast(SourceType, "mock"),
            manifest_path=manifest_path,
            artifacts_base=Path(temp_dir),
        )
        resolver = KitResolver(sources=[source])

        has_update, resolved, error_msg = check_for_updates(installed, resolver)

        assert has_update is True
        assert resolved is not None
        assert resolved.version == "2.0.0"
        assert error_msg is None


def test_check_for_updates_with_force_flag():
    """Test check_for_updates with force flag always returns update available."""
    installed = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=[],
        hooks=[],
    )

    # Create source with same version
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_path = Path(temp_dir) / "manifest.yaml"
        manifest_path.write_text("""
name: test-kit
version: "1.0.0"
description: Test kit
artifacts:
  agent: []
""")

        source = MockKitSource()
        source.resolved_kit = ResolvedKit(
            kit_id="test-kit",
            version="1.0.0",  # Same version
            source_type=cast(SourceType, "mock"),
            manifest_path=manifest_path,
            artifacts_base=Path(temp_dir),
        )
        resolver = KitResolver(sources=[source])

        # Without force: no update
        has_update, resolved, error_msg = check_for_updates(installed, resolver, force=False)
        assert has_update is False

        # With force: update available
        has_update, resolved, error_msg = check_for_updates(installed, resolver, force=True)
        assert has_update is True
        assert resolved is not None
        assert error_msg is None
