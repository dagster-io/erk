"""Tests for erk init capability list command."""

import re

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.gateway.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_capability_list_shows_available_capabilities() -> None:
    """Test that list command shows all registered capabilities."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Check section headers
        assert "Project capabilities:" in result.output
        assert "User capabilities:" in result.output
        # Check a project capability
        assert "learned-docs" in result.output
        assert "Autolearning documentation system" in result.output
        # Check a user capability
        assert "statusline" in result.output


def test_capability_list_works_without_repo() -> None:
    """Test that list command works outside a git repository."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # FakeGit returns None for git_common_dir when not in a repo
        git_ops = FakeGit(git_common_dirs={})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "learned-docs" in result.output


def test_capability_list_sorts_alphabetically() -> None:
    """Test that capabilities are sorted alphabetically within each scope."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "capability", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Extract capability names from output (they appear after "  " indentation)
        # Format is "  capability-name          description"
        capability_pattern = re.compile(r"^\s{2}(\S+)\s+", re.MULTILINE)

        # Split into project and user sections based on headers
        output_lines = result.output.split("\n")
        project_section: list[str] = []
        user_section: list[str] = []
        current_section: list[str] | None = None

        for line in output_lines:
            if "Project capabilities:" in line:
                current_section = project_section
            elif "User capabilities:" in line:
                current_section = user_section
            elif current_section is not None and line.strip():
                match = capability_pattern.match(line)
                if match:
                    current_section.append(match.group(1))

        # Verify each section is sorted alphabetically
        assert project_section == sorted(project_section), (
            f"Project capabilities not sorted: {project_section}"
        )
        assert user_section == sorted(user_section), f"User capabilities not sorted: {user_section}"

        # Verify we found capabilities in both sections
        assert len(project_section) > 0, "No project capabilities found"
        assert len(user_section) > 0, "No user capabilities found"
