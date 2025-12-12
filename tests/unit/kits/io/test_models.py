"""Tests for data models."""

import pytest

from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.models.kit import KitManifest
from erk.kits.models.registry import RegistryEntry


def test_installed_kit_immutable() -> None:
    """Test InstalledKit is frozen (immutable)."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=["artifact1.md"],
    )

    with pytest.raises(AttributeError):
        kit.version = "2.0.0"  # type: ignore


def test_project_config_creation() -> None:
    """Test ProjectConfig model creation."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=[],
    )

    config = ProjectConfig(
        version="1",
        kits={"test-kit": kit},
    )

    assert config.version == "1"
    assert "test-kit" in config.kits
    assert config.kits["test-kit"].kit_id == "test-kit"


def test_project_config_immutable() -> None:
    """Test ProjectConfig is frozen (immutable)."""
    config = ProjectConfig(
        version="1",
        kits={},
    )

    with pytest.raises(AttributeError):
        config.version = "2"  # type: ignore


def test_kit_manifest_required_fields() -> None:
    """Test KitManifest with required fields only."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={"agent": ["agents/test.md"]},
    )

    assert manifest.name == "test-kit"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Test kit"
    assert manifest.artifacts == {"agent": ["agents/test.md"]}
    assert manifest.license is None
    assert manifest.homepage is None


def test_kit_manifest_with_optional_fields() -> None:
    """Test KitManifest with all fields."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={"agent": ["agents/test.md"]},
        license="MIT",
        homepage="https://example.com",
    )

    assert manifest.license == "MIT"
    assert manifest.homepage == "https://example.com"


def test_kit_manifest_immutable() -> None:
    """Test KitManifest is frozen (immutable)."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
    )

    with pytest.raises(AttributeError):
        manifest.name = "other-kit"  # type: ignore


def test_registry_entry_required_fields() -> None:
    """Test RegistryEntry with required fields only."""
    entry = RegistryEntry(
        kit_id="test-kit",
        source_type="bundled",
        description="A test kit",
        version="1.0.0",
    )

    assert entry.kit_id == "test-kit"
    assert entry.source_type == "bundled"
    assert entry.description == "A test kit"
    assert entry.version == "1.0.0"


def test_registry_entry_immutable() -> None:
    """Test RegistryEntry is frozen (immutable)."""
    entry = RegistryEntry(
        kit_id="test-kit",
        source_type="bundled",
        description="A test kit",
        version="1.0.0",
    )

    with pytest.raises(AttributeError):
        entry.kit_id = "other-kit"  # type: ignore
