"""Tests for legacy kits.toml health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_kits_toml import check_legacy_kits_toml


def test_check_passes_when_no_kits_toml(tmp_path: Path) -> None:
    """Test check passes when .erk/kits.toml doesn't exist."""
    result = check_legacy_kits_toml(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert result.name == "legacy-kits-toml"
    assert "No legacy" in result.message


def test_check_passes_when_erk_dir_exists_but_no_kits_toml(tmp_path: Path) -> None:
    """Test check passes when .erk/ exists but kits.toml doesn't."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("[config]\n", encoding="utf-8")

    result = check_legacy_kits_toml(tmp_path)

    assert result.passed is True
    assert result.warning is not True
    assert "No legacy" in result.message


def test_check_warns_when_kits_toml_exists(tmp_path: Path) -> None:
    """Test check warns when .erk/kits.toml exists."""
    kits_file = tmp_path / ".erk" / "kits.toml"
    kits_file.parent.mkdir(parents=True)
    kits_file.write_text("[kits]\n", encoding="utf-8")

    result = check_legacy_kits_toml(tmp_path)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy-kits-toml"
    assert "Legacy kits.toml found" in result.message
    assert result.details is not None
    assert "kits.toml" in result.details
    assert "config.toml" in result.details
    assert "delete" in result.details.lower()
