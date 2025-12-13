"""Tests for deprecated dot-agent config health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder import check_deprecated_dot_agent_config


def test_check_deprecated_dot_agent_config_passes_when_no_pyproject(
    tmp_path: Path,
) -> None:
    """Test check passes when pyproject.toml doesn't exist."""
    result = check_deprecated_dot_agent_config(tmp_path)
    assert result.passed is True
    assert "No deprecated" in result.message


def test_check_deprecated_dot_agent_config_passes_when_no_tool_section(
    tmp_path: Path,
) -> None:
    """Test check passes when pyproject.toml has no [tool] section."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[project]
name = "test"
version = "1.0.0"
""",
        encoding="utf-8",
    )

    result = check_deprecated_dot_agent_config(tmp_path)
    assert result.passed is True
    assert "No deprecated" in result.message


def test_check_deprecated_dot_agent_config_passes_when_using_tool_erk(
    tmp_path: Path,
) -> None:
    """Test check passes when using correct [tool.erk] config."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[tool.erk]
some_setting = true
""",
        encoding="utf-8",
    )

    result = check_deprecated_dot_agent_config(tmp_path)
    assert result.passed is True
    assert "No deprecated" in result.message


def test_check_deprecated_dot_agent_config_fails_when_using_tool_dot_agent(
    tmp_path: Path,
) -> None:
    """Test check fails when using deprecated [tool.dot-agent] config."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[tool.dot-agent]
some_setting = true
""",
        encoding="utf-8",
    )

    result = check_deprecated_dot_agent_config(tmp_path)

    assert result.passed is False
    assert result.name == "deprecated dot-agent config"
    assert "[tool.dot-agent]" in result.message
    assert result.details is not None
    assert "[tool.erk]" in result.details
    assert "Remediation" in result.details
