"""Tests for I/O operations."""

from pathlib import Path

from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.io.registry import load_registry
from dot_agent_kit.io.state import create_default_config, load_project_config, save_project_config
from dot_agent_kit.models.config import InstalledKit


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

    from dot_agent_kit.models.config import ProjectConfig

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
        "kit_cli_commands:\n"
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
    assert len(manifest.kit_cli_commands) == 2
    assert manifest.kit_cli_commands[0].name == "compliance-reminder-hook"
    assert manifest.kit_cli_commands[0].path == "commands/compliance_reminder_hook.py"
    assert (
        manifest.kit_cli_commands[0].description
        == "Output dignified-python compliance reminder for UserPromptSubmit hook"
    )
    assert manifest.kit_cli_commands[1].name == "validate-exceptions"
    assert manifest.kit_cli_commands[1].path == "commands/validate_exceptions.py"
    assert manifest.kit_cli_commands[1].description == "Validate exception handling patterns"


def test_load_registry() -> None:
    """Test loading registry with entries."""
    registry = load_registry()

    assert isinstance(registry, list)
    assert len(registry) >= 1  # Should have at least devrun
    assert any(entry.kit_id == "devrun" for entry in registry)


def test_load_project_config_valid_bundled_kit(tmp_project: Path) -> None:
    """Test loading config with valid bundled kit."""
    # Write a config with bundled kit
    config_path = tmp_project / "dot-agent.toml"
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
    config_path = tmp_project / "dot-agent.toml"
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
    config_path = tmp_project / "dot-agent.toml"
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
    config_path = tmp_project / "dot-agent.toml"
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
    config_path = tmp_project / "dot-agent.toml"
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


def test_dev_mode_disabled_by_default(tmp_project: Path) -> None:
    """Test that dev_mode is False by default when not specified."""
    config_path = tmp_project / "dot-agent.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert config.dev_mode is False


def test_dev_mode_enabled_via_pyproject(tmp_project: Path) -> None:
    """Test that dev_mode is read from pyproject.toml."""
    # Create pyproject.toml with dev_mode enabled
    pyproject_path = tmp_project / "pyproject.toml"
    pyproject_path.write_text(
        """
[tool.dot-agent]
dev_mode = true
""",
        encoding="utf-8",
    )

    # Create dot-agent.toml
    config_path = tmp_project / "dot-agent.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert config.dev_mode is True


def test_dev_mode_disabled_via_pyproject(tmp_project: Path) -> None:
    """Test that dev_mode can be explicitly disabled in pyproject.toml."""
    # Create pyproject.toml with dev_mode disabled
    pyproject_path = tmp_project / "pyproject.toml"
    pyproject_path.write_text(
        """
[tool.dot-agent]
dev_mode = false
""",
        encoding="utf-8",
    )

    # Create dot-agent.toml
    config_path = tmp_project / "dot-agent.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert config.dev_mode is False


def test_dev_mode_no_pyproject(tmp_project: Path) -> None:
    """Test that dev_mode defaults to False when pyproject.toml doesn't exist."""
    # Only create dot-agent.toml (no pyproject.toml)
    config_path = tmp_project / "dot-agent.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert config.dev_mode is False


def test_dev_mode_pyproject_no_tool_section(tmp_project: Path) -> None:
    """Test that dev_mode defaults to False when pyproject.toml has no [tool] section."""
    # Create pyproject.toml without [tool] section
    pyproject_path = tmp_project / "pyproject.toml"
    pyproject_path.write_text(
        """
[project]
name = "test-project"
version = "1.0.0"
""",
        encoding="utf-8",
    )

    # Create dot-agent.toml
    config_path = tmp_project / "dot-agent.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert config.dev_mode is False


def test_load_config_from_new_location(tmp_project: Path) -> None:
    """Test loading config from new .agent/dot-agent.toml location."""
    # Create config in new location
    agent_dir = tmp_project / ".agent"
    agent_dir.mkdir()
    config_path = agent_dir / "dot-agent.toml"
    config_path.write_text(
        """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/test.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert "test-kit" in config.kits


def test_load_config_prefers_new_location_over_old(tmp_project: Path) -> None:
    """Test that new .agent/dot-agent.toml location takes precedence over old."""
    # Create config in BOTH locations with different content
    # Old location
    old_config_path = tmp_project / "dot-agent.toml"
    old_config_path.write_text(
        """
version = "1"

[kits.old-kit]
kit_id = "old-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/old.md"]
""",
        encoding="utf-8",
    )

    # New location
    agent_dir = tmp_project / ".agent"
    agent_dir.mkdir()
    new_config_path = agent_dir / "dot-agent.toml"
    new_config_path.write_text(
        """
version = "1"

[kits.new-kit]
kit_id = "new-kit"
source_type = "bundled"
version = "2.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/new.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    # Should have new-kit from new location, not old-kit
    assert "new-kit" in config.kits
    assert "old-kit" not in config.kits


def test_load_config_falls_back_to_old_location(tmp_project: Path) -> None:
    """Test that config falls back to old dot-agent.toml location."""
    # Create config ONLY in old location
    old_config_path = tmp_project / "dot-agent.toml"
    old_config_path.write_text(
        """
version = "1"

[kits.legacy-kit]
kit_id = "legacy-kit"
source_type = "bundled"
version = "1.0.0"
installed_at = "2024-01-01T00:00:00"
artifacts = ["agents/legacy.md"]
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_project)

    assert config is not None
    assert "legacy-kit" in config.kits


def test_save_config_creates_agent_directory(tmp_project: Path) -> None:
    """Test that save_project_config creates .agent/ directory if needed."""
    config = create_default_config()

    # .agent directory should not exist yet
    agent_dir = tmp_project / ".agent"
    assert not agent_dir.exists()

    # Save config
    save_project_config(tmp_project, config)

    # .agent directory should now exist
    assert agent_dir.exists()
    assert (agent_dir / "dot-agent.toml").exists()


def test_save_config_always_uses_new_location(tmp_project: Path) -> None:
    """Test that save_project_config always saves to .agent/dot-agent.toml."""
    config = create_default_config()

    # Save config
    save_project_config(tmp_project, config)

    # Should be saved to new location
    new_path = tmp_project / ".agent" / "dot-agent.toml"
    old_path = tmp_project / "dot-agent.toml"

    assert new_path.exists()
    assert not old_path.exists()
