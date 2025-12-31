"""Tests for legacy .erk/kits/ health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_erk_kits_folder import (
    check_legacy_erk_kits_folder,
)


def test_check_passes_when_no_kits_directory(tmp_path: Path) -> None:
    """Test check passes when .erk/kits/ doesn't exist."""
    result = check_legacy_erk_kits_folder(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert result.name == "legacy-erk-kits-folder"
    assert "No legacy" in result.message


def test_check_passes_when_erk_dir_has_no_kits(tmp_path: Path) -> None:
    """Test check passes when .erk/ exists but kits/ doesn't."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("[config]\n", encoding="utf-8")

    result = check_legacy_erk_kits_folder(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "No legacy" in result.message


def test_check_passes_when_kits_directory_is_empty(tmp_path: Path) -> None:
    """Test check passes when .erk/kits/ exists but is empty."""
    kits_dir = tmp_path / ".erk" / "kits"
    kits_dir.mkdir(parents=True)

    result = check_legacy_erk_kits_folder(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "empty directory" in result.message


def test_check_warns_when_kits_directory_has_content(tmp_path: Path) -> None:
    """Test check warns when .erk/kits/ contains content."""
    kit_dir = tmp_path / ".erk" / "kits" / "my-kit"
    kit_dir.mkdir(parents=True)
    (kit_dir / "kit.yaml").write_text("name: my-kit\n", encoding="utf-8")

    result = check_legacy_erk_kits_folder(tmp_path)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy-erk-kits-folder"
    assert "1 item" in result.message
    assert result.details is not None
    assert "kit system has been removed" in result.details
    assert "delete" in result.details.lower()


def test_check_counts_multiple_items(tmp_path: Path) -> None:
    """Test check counts all items in kits/ directory."""
    kits_dir = tmp_path / ".erk" / "kits"
    kits_dir.mkdir(parents=True)
    (kits_dir / "kit1").mkdir()
    (kits_dir / "kit2").mkdir()
    (kits_dir / "kit3").mkdir()

    result = check_legacy_erk_kits_folder(tmp_path)

    assert result.passed is True
    assert result.warning is True
    assert "3 item" in result.message
