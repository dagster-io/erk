"""Tests for erk doctor command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.doctor import doctor_cmd
from erk.core.health_checks import check_workflow_permissions
from erk.core.health_checks_dogfooder import check_deprecated_dot_agent_config
from erk_shared.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_doctor_runs_checks() -> None:
    """Test that doctor command runs and displays check results."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        # Command should succeed
        assert result.exit_code == 0

        # Should show section headers
        assert "Checking erk setup" in result.output
        assert "CLI Tools" in result.output
        assert "Repository Setup" in result.output

        # Should show erk version check
        assert "erk" in result.output.lower()


def test_doctor_shows_cli_availability() -> None:
    """Test that doctor shows CLI tool availability."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0

        # Should check for common tools (they may or may not be installed)
        # The output should mention each tool name
        output_lower = result.output.lower()
        assert "claude" in output_lower or "claude" in result.output
        assert "graphite" in output_lower or "gt" in output_lower
        assert "github" in output_lower or "gh" in output_lower


def test_doctor_shows_repository_status() -> None:
    """Test that doctor shows repository setup status."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should show repository check
        assert "Repository Setup" in result.output


def test_doctor_shows_summary() -> None:
    """Test that doctor shows a summary at the end."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should show either "All checks passed" or "check(s) failed"
        assert "passed" in result.output.lower() or "failed" in result.output.lower()


def test_doctor_shows_github_section() -> None:
    """Test that doctor shows GitHub section with auth and workflow permissions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        assert result.exit_code == 0
        # Should show GitHub section header
        assert "GitHub" in result.output


def test_check_workflow_permissions_no_origin_remote() -> None:
    """Test check_workflow_permissions when no origin remote is configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # FakeGit with no remote_urls configured - get_remote_url will raise ValueError
        # Use env.build_context() directly to avoid build_workspace_test_context
        # auto-adding a default remote URL
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # No remote_urls - get_remote_url will raise ValueError
        )

        ctx = env.build_context(git=git)

        result = check_workflow_permissions(ctx, env.cwd)

        # Should pass (info level) with appropriate message
        assert result.passed is True
        assert result.name == "workflow permissions"
        assert "No origin remote configured" in result.message


def test_check_workflow_permissions_non_github_remote() -> None:
    """Test check_workflow_permissions when remote is not GitHub."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # FakeGit with a non-GitHub remote URL
        # Use env.build_context() directly to avoid build_workspace_test_context
        # overwriting the remote URL
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://gitlab.com/owner/repo.git"},
        )

        ctx = env.build_context(git=git)

        result = check_workflow_permissions(ctx, env.cwd)

        # Should pass (info level) with appropriate message
        assert result.passed is True
        assert result.name == "workflow permissions"
        assert "Not a GitHub repository" in result.message


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
dev_mode = true
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
dev_mode = true
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


def test_check_deprecated_dot_agent_config_passes_when_no_dev_mode(
    tmp_path: Path,
) -> None:
    """Test check passes when [tool.dot-agent] has no dev_mode."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[tool.dot-agent]
other_setting = "value"
""",
        encoding="utf-8",
    )

    result = check_deprecated_dot_agent_config(tmp_path)
    assert result.passed is True
    assert "No deprecated" in result.message


def test_doctor_shows_early_dogfooder_section_on_deprecated_config() -> None:
    """Test that doctor shows Early Dogfooder section when deprecated config found."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create deprecated pyproject.toml config
        pyproject_path = env.cwd / "pyproject.toml"
        pyproject_path.write_text(
            """
[tool.dot-agent]
dev_mode = true
""",
            encoding="utf-8",
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(doctor_cmd, [], obj=ctx)

        # Should show Early Dogfooder section
        assert "Early Dogfooder" in result.output
        assert "deprecated" in result.output.lower()
        assert "[tool.erk]" in result.output
