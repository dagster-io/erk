"""Unit tests for implement_shared helpers."""

import pytest
from click import ClickException
from click.testing import CliRunner

from erk.cli.commands.implement_shared import (
    extract_plan_from_current_branch,
    validate_flags,
)
from erk_shared.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_extract_plan_from_current_branch_with_p_prefix() -> None:
    """Test extraction from branch with P prefix."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["P123-fix-bug-01-16-1200"]},
            current_branches={env.cwd: "P123-fix-bug-01-16-1200"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result == "123"


def test_extract_plan_from_current_branch_with_large_issue_number() -> None:
    """Test extraction works with large issue numbers."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["P4567-feature-branch-01-16-1200"]},
            current_branches={env.cwd: "P4567-feature-branch-01-16-1200"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result == "4567"


def test_extract_plan_from_current_branch_returns_none_for_non_plan_branch() -> None:
    """Test returns None for non-plan branches."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["feature-branch"]},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result is None


def test_extract_plan_from_current_branch_returns_none_for_main() -> None:
    """Test returns None for main branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result is None


def test_extract_plan_handles_no_current_branch() -> None:
    """Test returns None when no current branch (detached HEAD)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: []},
            # current_branches not set means get_current_branch returns None
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result is None


def test_extract_plan_from_legacy_branch_format() -> None:
    """Test extraction from legacy branch format without P prefix."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["123-fix-bug-01-16-1200"]},
            current_branches={env.cwd: "123-fix-bug-01-16-1200"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        # Legacy format is supported
        assert result == "123"


class TestValidateFlags:
    """Tests for validate_flags function."""

    def test_valid_interactive_mode(self) -> None:
        """Test valid interactive mode (no submit, no no-interactive)."""
        # Should not raise
        validate_flags(
            submit=False,
            no_interactive=False,
            script=False,
            docker=False,
            codespace=None,
        )

    def test_valid_non_interactive_with_submit(self) -> None:
        """Test valid non-interactive mode with submit."""
        # Should not raise
        validate_flags(
            submit=True,
            no_interactive=True,
            script=False,
            docker=False,
            codespace=None,
        )

    def test_submit_requires_non_interactive(self) -> None:
        """Test that submit without no-interactive raises error."""
        with pytest.raises(ClickException) as exc_info:
            validate_flags(
                submit=True,
                no_interactive=False,
                script=False,
                docker=False,
                codespace=None,
            )
        assert "--submit requires --no-interactive" in str(exc_info.value)

    def test_submit_with_script_allowed(self) -> None:
        """Test that submit with script is allowed (script generates shell code)."""
        # Should not raise
        validate_flags(
            submit=True,
            no_interactive=False,
            script=True,
            docker=False,
            codespace=None,
        )

    def test_no_interactive_and_script_mutually_exclusive(self) -> None:
        """Test that no-interactive and script are mutually exclusive."""
        with pytest.raises(ClickException) as exc_info:
            validate_flags(
                submit=False,
                no_interactive=True,
                script=True,
                docker=False,
                codespace=None,
            )
        assert "--no-interactive and --script are mutually exclusive" in str(exc_info.value)

    def test_docker_and_codespace_mutually_exclusive(self) -> None:
        """Test that docker and codespace are mutually exclusive."""
        with pytest.raises(ClickException) as exc_info:
            validate_flags(
                submit=False,
                no_interactive=False,
                script=False,
                docker=True,
                codespace="mybox",
            )
        assert "--docker and --codespace are mutually exclusive" in str(exc_info.value)

    def test_docker_and_codespace_empty_string_mutually_exclusive(self) -> None:
        """Test that docker and codespace with empty string are mutually exclusive."""
        # Empty string means "use default codespace"
        with pytest.raises(ClickException) as exc_info:
            validate_flags(
                submit=False,
                no_interactive=False,
                script=False,
                docker=True,
                codespace="",
            )
        assert "--docker and --codespace are mutually exclusive" in str(exc_info.value)

    def test_docker_alone_valid(self) -> None:
        """Test that docker alone is valid."""
        # Should not raise
        validate_flags(
            submit=False,
            no_interactive=False,
            script=False,
            docker=True,
            codespace=None,
        )

    def test_codespace_alone_valid(self) -> None:
        """Test that codespace alone is valid."""
        # Should not raise
        validate_flags(
            submit=False,
            no_interactive=False,
            script=False,
            docker=False,
            codespace="mybox",
        )

    def test_codespace_default_valid(self) -> None:
        """Test that codespace with empty string (default) is valid."""
        # Should not raise - empty string means use default
        validate_flags(
            submit=False,
            no_interactive=False,
            script=False,
            docker=False,
            codespace="",
        )
