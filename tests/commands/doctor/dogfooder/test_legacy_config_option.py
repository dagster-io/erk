"""Tests for legacy config option health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_config_option import (
    check_legacy_config_option,
)


def test_check_passes_when_no_config_file(tmp_path: Path) -> None:
    """Test check passes when .erk/config.toml doesn't exist."""
    result = check_legacy_config_option(tmp_path)

    assert result.passed is True
    assert result.name == "legacy-config-option"
    assert "No .erk/config.toml" in result.message


def test_check_passes_when_config_has_no_deprecated_options(tmp_path: Path) -> None:
    """Test check passes when config has no deprecated options."""
    config_path = tmp_path / ".erk" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[graphite]\nauto_restack_require_dangerous_flag = true\n",
        encoding="utf-8",
    )

    result = check_legacy_config_option(tmp_path)

    assert result.passed is True
    assert "No deprecated" in result.message


def test_check_fails_when_deprecated_option_found(tmp_path: Path) -> None:
    """Test check fails when deprecated option is found."""
    config_path = tmp_path / ".erk" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[graphite]\nauto_restack_skip_dangerous = true\n",
        encoding="utf-8",
    )

    result = check_legacy_config_option(tmp_path)

    assert result.passed is False  # Failure, not warning
    assert result.name == "legacy-config-option"
    assert "1 deprecated config option" in result.message
    assert result.details is not None
    assert "auto_restack_skip_dangerous" in result.details
    assert "auto_restack_require_dangerous_flag" in result.details
    assert "inverted logic" in result.details


def test_check_provides_migration_path(tmp_path: Path) -> None:
    """Test check provides migration path in details."""
    config_path = tmp_path / ".erk" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[graphite]\nauto_restack_skip_dangerous = false\n",
        encoding="utf-8",
    )

    result = check_legacy_config_option(tmp_path)

    assert result.passed is False
    assert result.details is not None
    assert "->" in result.details  # Shows old -> new mapping
    assert "config.toml" in result.details
