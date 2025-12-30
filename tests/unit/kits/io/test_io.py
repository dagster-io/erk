"""Tests for I/O operations."""

from pathlib import Path

from erk.kits.io.manifest import load_kit_manifest
from erk.kits.io.state import create_default_config, load_project_config, save_project_config
from erk.kits.models.config import InstalledKit


def test_load_save_project_config(tmp_project: Path) -> None:
    """Test round-trip TOML read/write."""
    config = create_default_config()

    # Add a kit
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=["artifact1.md"],
    )

    from erk.kits.models.config import ProjectConfig

    config = ProjectConfig(
        version="1",
        kits={"test-kit": kit},
    )

    # Save and load
    save_project_config(tmp_project, config)
    loaded_config = load_project_config(tmp_project)

    assert loaded_config is not None
    assert loaded_config.version == "1"
    assert "test-kit" in loaded_config.kits
    assert loaded_config.kits["test-kit"].kit_id == "test-kit"
    assert loaded_config.kits["test-kit"].version == "1.0.0"


def test_load_nonexistent_config(tmp_project: Path) -> None:
    """Test loading returns None when file doesn't exist."""
    config = load_project_config(tmp_project)
    assert config is None


def test_create_default_config() -> None:
    """Test default config creation."""
    config = create_default_config()

    assert config.version == "1"
    assert len(config.kits) == 0


def test_load_kit_manifest(tmp_path: Path) -> None:
    """Test kit.yaml parsing."""
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test kit\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test.md\n"
        "license: MIT\n"
        "homepage: https://example.com\n",
        encoding="utf-8",
    )

    manifest = load_kit_manifest(manifest_path)

    assert manifest.name == "test-kit"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Test kit"
    assert manifest.artifacts == {"agent": ["agents/test.md"]}
    assert manifest.license == "MIT"
    assert manifest.homepage == "https://example.com"


def test_load_kit_manifest_minimal(tmp_path: Path) -> None:
    """Test kit.yaml with minimal fields."""
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text(
        "name: test-kit\nversion: 1.0.0\ndescription: Test kit\n",
        encoding="utf-8",
    )

    manifest = load_kit_manifest(manifest_path)

    assert manifest.name == "test-kit"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Test kit"
    assert manifest.artifacts == {}
    assert manifest.license is None
    assert manifest.homepage is None


def test_load_kit_manifest_with_commands(tmp_path: Path) -> None:
    """Test kit.yaml with kit cli commands section."""
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test kit\n"
        "scripts:\n"
        "  - name: compliance-reminder-hook\n"
        "    path: commands/compliance_reminder_hook.py\n"
        "    description: Output dignified-python compliance reminder for UserPromptSubmit hook\n"
        "  - name: validate-exceptions\n"
        "    path: commands/validate_exceptions.py\n"
        "    description: Validate exception handling patterns\n",
        encoding="utf-8",
    )

    manifest = load_kit_manifest(manifest_path)

    assert manifest.name == "test-kit"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Test kit"
    assert len(manifest.scripts) == 2
    assert manifest.scripts[0].name == "compliance-reminder-hook"
    assert manifest.scripts[0].path == "commands/compliance_reminder_hook.py"
    assert (
        manifest.scripts[0].description
        == "Output dignified-python compliance reminder for UserPromptSubmit hook"
    )
    assert manifest.scripts[1].name == "validate-exceptions"
    assert manifest.scripts[1].path == "commands/validate_exceptions.py"
    assert manifest.scripts[1].description == "Validate exception handling patterns"


def test_load_project_config_valid_bundled_kit(tmp_project: Path) -> None:
    """Test loading config with valid bundled kit."""
    # Write a config with bundled kit
    erk_dir = tmp_project / ".erk"
    erk_dir.mkdir(exist_ok=True)
    config_path = erk_dir / "kits.toml"
    config_path.write_text(
        """
version = "1"

[kits.devrun]
kit_id = "devrun"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/devrun.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert "devrun" in config.kits
    assert config.kits["devrun"].kit_id == "devrun"
    assert config.kits["devrun"].source_type == "bundled"
    assert config.kits["devrun"].version == "1.0.0"


def test_load_project_config_valid_package_kit(tmp_project: Path) -> None:
    """Test loading config with valid package kit."""
    # Write a config with package kit
    erk_dir = tmp_project / ".erk"
    erk_dir.mkdir(exist_ok=True)
    config_path = erk_dir / "kits.toml"
    config_path.write_text(
        """
version = "1"

[kits.my-custom-kit]
kit_id = "my-custom-kit"
source_type = "package"
version = "2.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["skills/custom.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert "my-custom-kit" in config.kits
    assert config.kits["my-custom-kit"].kit_id == "my-custom-kit"
    assert config.kits["my-custom-kit"].source_type == "package"
    assert config.kits["my-custom-kit"].version == "2.0.0"


def test_load_project_config_missing_kit_id(tmp_project: Path) -> None:
    """Test loading config with missing kit_id field raises KeyError."""
    # Write a config without kit_id
    erk_dir = tmp_project / ".erk"
    erk_dir.mkdir(exist_ok=True)
    config_path = erk_dir / "kits.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(KeyError) as exc_info:
        load_project_config(tmp_project)

    assert "kit_id" in str(exc_info.value)
    assert "test-kit" in str(exc_info.value)


def test_load_project_config_missing_source_type(tmp_project: Path) -> None:
    """Test loading config with missing source_type field raises KeyError."""
    # Write a config without source_type
    erk_dir = tmp_project / ".erk"
    erk_dir.mkdir(exist_ok=True)
    config_path = erk_dir / "kits.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    import pytest

    with pytest.raises(KeyError) as exc_info:
        load_project_config(tmp_project)

    assert "source_type" in str(exc_info.value)
    assert "test-kit" in str(exc_info.value)


def test_load_project_config_various_identifier_formats(tmp_project: Path) -> None:
    """Test loading config with various valid identifier formats."""
    # Write a config with identifiers using dashes, underscores, numbers
    erk_dir = tmp_project / ".erk"
    erk_dir.mkdir(exist_ok=True)
    config_path = erk_dir / "kits.toml"
    config_path.write_text(
        """
version = "1"

[kits.kit-with-dashes]
kit_id = "kit-with-dashes"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]

[kits.kit_with_underscores]
kit_id = "kit_with_underscores"
source_type = "package"
version = "2.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test2.md"]

[kits.kit123]
kit_id = "kit123"
source_type = "bundled"
version = "3.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test3.md"]

[kits.kit-mix_123]
kit_id = "kit-mix_123"
source_type = "package"
version = "4.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test4.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert len(config.kits) == 4
    assert "kit-with-dashes" in config.kits
    assert "kit_with_underscores" in config.kits
    assert "kit123" in config.kits
    assert "kit-mix_123" in config.kits

    # Verify all loaded correctly
    assert config.kits["kit-with-dashes"].kit_id == "kit-with-dashes"
    assert config.kits["kit_with_underscores"].kit_id == "kit_with_underscores"
    assert config.kits["kit123"].kit_id == "kit123"
    assert config.kits["kit-mix_123"].kit_id == "kit-mix_123"


def test_save_config_creates_erk_directory(tmp_project: Path) -> None:
    """Test that save_project_config creates .erk/ directory if needed."""
    config = create_default_config()

    # .erk directory should not exist yet
    erk_dir = tmp_project / ".erk"
    assert not erk_dir.exists()

    # Save config
    save_project_config(tmp_project, config)

    # .erk directory should now exist
    assert erk_dir.exists()
    assert (erk_dir / "kits.toml").exists()


def test_save_config_uses_erk_location(tmp_project: Path) -> None:
    """Test that save_project_config saves to .erk/kits.toml."""
    config = create_default_config()

    # Save config
    save_project_config(tmp_project, config)

    # Should be saved to .erk/kits.toml
    config_path = tmp_project / ".erk" / "kits.toml"

    assert config_path.exists()
