"""Tests for legacy kit.yaml health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_kit_yaml import check_legacy_kit_yaml


def test_check_passes_when_no_kit_yaml_files(tmp_path: Path) -> None:
    """Test check passes when no kit.yaml files exist."""
    result = check_legacy_kit_yaml(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert result.name == "legacy kit.yaml"
    assert "No legacy" in result.message


def test_check_passes_when_claude_dir_has_no_kit_yaml(tmp_path: Path) -> None:
    """Test check passes when .claude/ exists but has no kit.yaml."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}", encoding="utf-8")

    result = check_legacy_kit_yaml(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "No legacy" in result.message


def test_check_warns_when_kit_yaml_in_claude_dir(tmp_path: Path) -> None:
    """Test check warns when kit.yaml exists in .claude/."""
    kit_dir = tmp_path / ".claude" / "kits" / "my-kit"
    kit_dir.mkdir(parents=True)
    (kit_dir / "kit.yaml").write_text("name: my-kit\n", encoding="utf-8")

    result = check_legacy_kit_yaml(tmp_path)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy kit.yaml"
    assert "1 legacy kit.yaml" in result.message
    assert result.details is not None
    assert "kit.yaml" in result.details
    assert "delete" in result.details.lower()


def test_check_warns_when_kit_yaml_in_erk_kits_dir(tmp_path: Path) -> None:
    """Test check warns when kit.yaml exists in .erk/kits/."""
    kit_dir = tmp_path / ".erk" / "kits" / "my-kit"
    kit_dir.mkdir(parents=True)
    (kit_dir / "kit.yaml").write_text("name: my-kit\n", encoding="utf-8")

    result = check_legacy_kit_yaml(tmp_path)

    assert result.passed is True
    assert result.warning is True
    assert "1 legacy kit.yaml" in result.message


def test_check_counts_multiple_kit_yaml_files(tmp_path: Path) -> None:
    """Test check counts all kit.yaml files found."""
    # Create kit.yaml in .claude/
    kit1_dir = tmp_path / ".claude" / "kits" / "kit1"
    kit1_dir.mkdir(parents=True)
    (kit1_dir / "kit.yaml").write_text("name: kit1\n", encoding="utf-8")

    # Create kit.yaml in .erk/kits/
    kit2_dir = tmp_path / ".erk" / "kits" / "kit2"
    kit2_dir.mkdir(parents=True)
    (kit2_dir / "kit.yaml").write_text("name: kit2\n", encoding="utf-8")

    result = check_legacy_kit_yaml(tmp_path)

    assert result.passed is True
    assert result.warning is True
    assert "2 legacy kit.yaml" in result.message


def test_check_finds_nested_kit_yaml_files(tmp_path: Path) -> None:
    """Test check finds kit.yaml files in nested subdirectories."""
    nested_dir = tmp_path / ".claude" / "deep" / "nested" / "kit"
    nested_dir.mkdir(parents=True)
    (nested_dir / "kit.yaml").write_text("name: nested\n", encoding="utf-8")

    result = check_legacy_kit_yaml(tmp_path)

    assert result.passed is True
    assert result.warning is True
    assert "1 legacy kit.yaml" in result.message
