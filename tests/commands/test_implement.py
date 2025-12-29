"""Tests for unified implement command."""

import os
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import _detect_target_type, implement
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def _create_sample_plan_issue(issue_number: str = "42") -> Plan:
    """Create a sample plan issue for testing."""
    return Plan(
        plan_identifier=issue_number,
        title="Add Authentication Feature",
        body="# Implementation Plan\n\nAdd user authentication to the application.",
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{issue_number}",
        labels=["erk-plan", "enhancement"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )


# Target Detection Tests


def test_detect_issue_number_with_hash() -> None:
    """Test detection of issue numbers with # prefix."""
    target_info = _detect_target_type("#123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_plain_number_as_issue() -> None:
    """Test that plain numbers are treated as GitHub issue numbers."""
    target_info = _detect_target_type("123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_issue_url() -> None:
    """Test detection of GitHub issue URLs."""
    url = "https://github.com/user/repo/issues/456"
    target_info = _detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "456"


def test_detect_issue_url_with_path() -> None:
    """Test detection of GitHub issue URLs with additional path."""
    url = "https://github.com/user/repo/issues/789#issuecomment-123"
    target_info = _detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "789"


def test_detect_relative_numeric_file() -> None:
    """Test that numeric files with ./ prefix are treated as file paths."""
    target_info = _detect_target_type("./123")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_plain_and_prefixed_numbers_equivalent() -> None:
    """Test that plain and prefixed numbers both resolve to issue numbers."""
    result_plain = _detect_target_type("809")
    result_prefixed = _detect_target_type("#809")
    assert result_plain.target_type == result_prefixed.target_type == "issue_number"
    assert result_plain.issue_number == result_prefixed.issue_number == "809"


def test_detect_file_path() -> None:
    """Test detection of file paths."""
    target_info = _detect_target_type("./my-feature-plan.md")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_detect_file_path_with_special_chars() -> None:
    """Test detection of file paths with special characters."""
    target_info = _detect_target_type("/path/to/my-plan.md")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


# GitHub Issue Mode Tests


def test_implement_from_plain_issue_number() -> None:
    """Test implementing from GitHub issue number without # prefix."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Test with plain number (no # prefix)
        result = runner.invoke(implement, ["123", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        # Branch name: sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
        assert "123-add-authentication-feature-01-15-1430" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists with correct issue number
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        issue_json_path = worktree_paths[0] / ".impl" / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json_content


# GitHub Issue Mode Tests


def test_implement_from_issue_number() -> None:
    """Test implementing from GitHub issue number with # prefix."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        # Branch name: sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
        assert "42-add-authentication-feature-01-15-1430" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        impl_path = worktree_paths[0] / ".impl"
        assert impl_path.exists()
        assert (impl_path / "plan.md").exists()
        assert (impl_path / "progress.md").exists()
        assert (impl_path / "issue.json").exists()


def test_implement_from_issue_url() -> None:
    """Test implementing from GitHub issue URL."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        url = "https://github.com/owner/repo/issues/123"
        result = runner.invoke(implement, [url, "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert len(git.added_worktrees) == 1

        # Verify issue.json contains correct issue number
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        issue_json_path = worktree_paths[0] / ".impl" / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json_content


def test_implement_from_issue_with_custom_name() -> None:
    """Test implementing from issue with custom worktree name."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(
            implement, ["#42", "--worktree-name", "my-custom-feature", "--script"], obj=ctx
        )

        assert result.exit_code == 0
        assert "my-custom-feature" in result.output

        worktree_path, _ = git.added_worktrees[0]
        assert "my-custom-feature" in str(worktree_path)


def test_implement_from_issue_fails_without_erk_plan_label() -> None:
    """Test that command fails when issue doesn't have erk-plan label."""
    plan_issue = Plan(
        plan_identifier="42",
        title="Regular Issue",
        body="Not a plan issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["bug"],  # Missing "erk-plan" label
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "erk-plan" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_from_issue_fails_when_not_found() -> None:
    """Test that command fails when issue doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#999", "--dry-run"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_from_issue_dry_run() -> None:
    """Test dry-run mode for issue implementation."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would create worktree" in result.output
        assert "Add Authentication Feature" in result.output
        assert len(git.added_worktrees) == 0


# Plan File Mode Tests


def test_implement_from_plan_file() -> None:
    """Test implementing from plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert "my-feature" in result.output

        # Verify worktree created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists with plan content
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        impl_plan = worktree_paths[0] / ".impl" / "plan.md"
        assert impl_plan.exists()
        assert impl_plan.read_text(encoding="utf-8") == plan_content

        # Verify original plan file deleted (move semantics)
        assert not plan_file.exists()


def test_implement_from_plan_file_with_custom_name() -> None:
    """Test implementing from plan file with custom worktree name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(
            implement, [str(plan_file), "--worktree-name", "custom-name", "--script"], obj=ctx
        )

        assert result.exit_code == 0
        assert "custom-name" in result.output

        worktree_path, _ = git.added_worktrees[0]
        assert "custom-name" in str(worktree_path)


def test_implement_from_plan_file_strips_plan_suffix() -> None:
    """Test that '-plan' suffix is stripped from plan filenames."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file with -plan suffix
        plan_file = env.cwd / "authentication-feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        # Verify -plan suffix was stripped
        assert "authentication-feature" in result.output
        # Ensure no "-plan" in worktree name
        worktree_path, _ = git.added_worktrees[0]
        worktree_name = str(worktree_path.name)
        assert "-plan" not in worktree_name or worktree_name.endswith("-plan") is False


def test_implement_from_plan_file_fails_when_not_found() -> None:
    """Test that command fails when plan file doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(implement, ["nonexistent-plan.md", "--dry-run"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "not found" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_from_plan_file_dry_run() -> None:
    """Test dry-run mode for plan file implementation."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would create worktree" in result.output
        assert str(plan_file) in result.output
        assert len(git.added_worktrees) == 0
        # Verify plan file NOT deleted in dry-run
        assert plan_file.exists()


# Branch Conflict Tests


def test_implement_issue_mode_uses_linked_branch_not_worktree_name() -> None:
    """Test that issue mode uses computed branch name, ignoring --worktree-name for branch.

    The branch is computed from the issue number and title with a timestamp suffix.
    The --worktree-name flag only affects the worktree directory name, not the branch.
    """
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "existing-branch"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Even though "existing-branch" exists, issue mode uses a computed branch name
        # (e.g., "42-add-authentication-feature-01-15-1430") so this should succeed - the
        # worktree name is "existing-branch" but the branch is derived from issue title
        result = runner.invoke(
            implement, ["#42", "--worktree-name", "existing-branch", "--script"], obj=ctx
        )

        # Should succeed because the branch doesn't conflict with "existing-branch"
        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Verify worktree was created with custom name but branch created directly
        assert len(git.added_worktrees) == 1
        worktree_path, _ = git.added_worktrees[0]
        assert "existing-branch" in str(worktree_path)


def test_implement_fails_when_branch_exists_file_mode() -> None:
    """Test that file mode fails when branch already exists with explicit name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "existing-branch"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(
            implement, [str(plan_file), "--worktree-name", "existing-branch"], obj=ctx
        )

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "already exists" in result.output
        # Should suggest -f flag or choosing a different name (not suggest --worktree-name)
        assert "Use -f to delete" in result.output or "choose a different name" in result.output
        assert len(git.added_worktrees) == 0


# Submit Flag Tests


def test_implement_with_submit_flag_from_issue() -> None:
    """Test --submit flag with --script from issue includes command chain in script."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Use --script --submit to generate activation script with all commands
        result = runner.invoke(implement, ["#42", "--script", "--submit"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Script should be created
        assert "erk-implement-" in result.output
        assert ".sh" in result.output


def test_implement_with_submit_flag_from_file() -> None:
    """Test implementing from file with --submit flag and --script generates script."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Feature Plan\n\nImplement feature.", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script", "--submit"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Script should be created
        assert "erk-implement-" in result.output
        assert ".sh" in result.output

        # Verify plan file was deleted (moved to worktree)
        assert not plan_file.exists()


def test_implement_without_submit_uses_default_command() -> None:
    """Test that default behavior (without --submit) still works unchanged."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Verify script has only implement-plan command (not CI/submit)
        assert "erk-implement-" in result.output
        assert ".sh" in result.output


def test_implement_submit_in_script_mode() -> None:
    """Test that --script --submit combination generates correct activation script."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--submit", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify script content contains chained commands
        assert "/erk:plan-implement" in script_content
        assert "/fast-ci" in script_content
        assert "/gt:pr-submit" in script_content

        # Verify commands are chained with &&
        assert "&&" in script_content


def test_implement_submit_with_dry_run() -> None:
    """Test that --submit --dry-run shows all commands that would be executed."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(
            implement, ["#42", "--no-interactive", "--submit", "--dry-run"], obj=ctx
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify execution mode shown
        assert "Execution mode: non-interactive" in result.output

        # Verify all three commands shown in dry-run output
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:pr-submit" in result.output

        # Verify no worktree was actually created
        assert len(git.added_worktrees) == 0


# Graphite Configuration Tests


def test_implement_uses_git_when_graphite_disabled() -> None:
    """Test that implement uses standard git workflow when use_graphite=false.

    Note: Tests with use_graphite=true require graphite subprocess integration
    (gt create command), which should be tested at the integration level with
    real gt commands, not in unit tests.
    """
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        # Build context with use_graphite=False (default)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, use_graphite=False)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        # Verify worktree was created
        assert len(git.added_worktrees) == 1


def test_implement_plan_file_uses_git_when_graphite_disabled() -> None:
    """Test that plan file mode uses standard git workflow when use_graphite=false.

    Note: Tests with use_graphite=true require graphite subprocess integration.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        # Build context with use_graphite=False (default)
        ctx = build_workspace_test_context(env, git=git, use_graphite=False)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        # Verify worktree was created
        assert len(git.added_worktrees) == 1


def test_implement_from_issue_tracks_branch_with_graphite() -> None:
    """Test erk implement calls ctx.graphite.track_branch() when use_graphite=True.

    This mirrors test_create_from_issue_tracks_branch_with_graphite from test_create.py.
    Verifies that when:
    1. use_graphite=True in global config
    2. erk implement <issue> is called
    3. Then ctx.graphite.track_branch() is called with correct parameters

    The key assertion is that track_branch is called with repo_root (not worktree path)
    as the cwd argument, since Graphite metadata exists at the repo root.
    """
    from erk_shared.gateway.graphite.fake import FakeGraphite

    plan_issue = _create_sample_plan_issue("500")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"500": plan_issue})
        fake_graphite = FakeGraphite()

        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            graphite=fake_graphite,
            use_graphite=True,
        )

        result = runner.invoke(implement, ["#500", "--script"], obj=ctx)

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr if hasattr(result, 'stderr') else 'N/A'}")
            print(f"stdout: {result.output}")
        assert result.exit_code == 0

        # Assert: Worktree was created
        assert len(git.added_worktrees) == 1

        # Assert: track_branch was called with correct parameters
        # The branch is created directly via git, then tracked with Graphite
        assert len(fake_graphite.track_branch_calls) == 1, (
            f"Expected 1 track_branch call, got {len(fake_graphite.track_branch_calls)}: "
            f"{fake_graphite.track_branch_calls}"
        )

        cwd_path, branch_name, parent_branch = fake_graphite.track_branch_calls[0]

        # Branch name should contain the issue number
        assert "500" in branch_name, f"Branch name should contain issue number: {branch_name}"

        # Parent should be trunk branch (main)
        assert parent_branch == "main", f"Parent branch should be 'main', got: {parent_branch}"

        # Critical: cwd_path should be repo_root, not the new worktree path
        # This is the bug fix we're testing - track_branch must run from repo_root
        # where Graphite metadata exists
        worktree_path = git.added_worktrees[0][0]
        assert cwd_path != worktree_path, (
            f"track_branch should be called with repo_root, not worktree path. "
            f"Got cwd_path={cwd_path}, worktree_path={worktree_path}"
        )


# Dangerous Flag Tests


def test_implement_with_dangerous_flag_in_script_mode() -> None:
    """Test that --dangerous flag adds --dangerously-skip-permissions to generated script."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--dangerous", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify --dangerously-skip-permissions flag is present
        assert "--dangerously-skip-permissions" in script_content
        expected_cmd = (
            "claude --permission-mode acceptEdits "
            "--dangerously-skip-permissions /erk:plan-implement"
        )
        assert expected_cmd in script_content


def test_implement_without_dangerous_flag_in_script_mode() -> None:
    """Test that script without --dangerous flag does not include --dangerously-skip-permissions."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify --dangerously-skip-permissions flag is NOT present
        assert "--dangerously-skip-permissions" not in script_content
        # But standard flags should be present
        assert "claude --permission-mode acceptEdits /erk:plan-implement" in script_content


def test_implement_with_dangerous_and_submit_flags() -> None:
    """Test that --dangerous --submit combination adds flag to all three commands."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--dangerous", "--submit", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify all three commands have the dangerous flag
        assert script_content.count("--dangerously-skip-permissions") == 3
        expected_implement = (
            "claude --permission-mode acceptEdits "
            "--dangerously-skip-permissions /erk:plan-implement"
        )
        expected_ci = "claude --permission-mode acceptEdits --dangerously-skip-permissions /fast-ci"
        expected_submit = (
            "claude --permission-mode acceptEdits --dangerously-skip-permissions /gt:pr-submit"
        )
        assert expected_implement in script_content
        assert expected_ci in script_content
        assert expected_submit in script_content


def test_implement_with_dangerous_flag_in_dry_run() -> None:
    """Test that --dangerous flag shows in dry-run output."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--dangerous", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify dangerous flag is shown in the command
        assert "--dangerously-skip-permissions" in result.output
        expected_cmd = (
            "claude --permission-mode acceptEdits "
            "--dangerously-skip-permissions /erk:plan-implement"
        )
        assert expected_cmd in result.output

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_implement_with_dangerous_and_submit_in_dry_run() -> None:
    """Test that --dangerous --submit shows flag in all three commands during dry-run."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(
            implement,
            ["#42", "--dangerous", "--no-interactive", "--submit", "--dry-run"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify all three commands show the dangerous flag
        assert result.output.count("--dangerously-skip-permissions") == 3

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_implement_plan_file_with_dangerous_flag() -> None:
    """Test that --dangerous flag works with plan file mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--dangerous", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify dangerous flag is present
        assert "--dangerously-skip-permissions" in script_content

        # Verify plan file was moved to worktree (deleted from original location)
        assert not plan_file.exists()


def test_implement_with_dangerous_shows_in_manual_instructions() -> None:
    """Test that --dangerous flag appears in manual instructions when shell integration disabled."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Use --script flag to generate activation script with dangerous flag
        result = runner.invoke(implement, ["#42", "--dangerous", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Verify dangerous flag shown in script file
        assert result.stdout
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")
        assert "--dangerously-skip-permissions" in script_content


# Execution Mode Tests


def test_interactive_mode_calls_executor() -> None:
    """Verify interactive mode calls executor.execute_interactive."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        # Interactive mode is the default (no --no-interactive flag)
        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0

        # Verify execute_interactive was called, not execute_command
        assert len(executor.interactive_calls) == 1
        assert len(executor.executed_commands) == 0

        worktree_path, dangerous, command, target_subpath = executor.interactive_calls[0]
        # Branch name: sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
        assert "42-add-authentication-feature-01-15-1430" in str(worktree_path)
        assert dangerous is False
        assert command == "/erk:plan-implement"
        # No relative path preservation when running from worktree root
        assert target_subpath is None


def test_interactive_mode_with_dangerous_flag() -> None:
    """Verify interactive mode passes dangerous flag to executor."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42", "--dangerous"], obj=ctx)

        assert result.exit_code == 0

        # Verify dangerous flag was passed to execute_interactive
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath = executor.interactive_calls[0]
        assert dangerous is True
        assert command == "/erk:plan-implement"


def test_interactive_mode_from_plan_file() -> None:
    """Verify interactive mode works with plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file)], obj=ctx)

        assert result.exit_code == 0

        # Verify execute_interactive was called
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath = executor.interactive_calls[0]
        assert "my-feature" in str(worktree_path)
        assert dangerous is False
        assert command == "/erk:plan-implement"

        # Verify plan file was deleted (moved to worktree)
        assert not plan_file.exists()


def test_interactive_mode_fails_when_claude_not_available() -> None:
    """Verify interactive mode fails gracefully when Claude CLI not available."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=False)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        # Should fail with error about Claude CLI not found
        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output


def test_submit_without_non_interactive_errors() -> None:
    """Verify --submit requires --no-interactive."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--submit"], obj=ctx)

        assert result.exit_code != 0
        assert "--submit requires --no-interactive" in result.output


def test_script_and_non_interactive_errors() -> None:
    """Verify --script and --no-interactive are mutually exclusive."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--no-interactive", "--script"], obj=ctx)

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


def test_non_interactive_executes_single_command() -> None:
    """Verify --no-interactive runs executor for implementation."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42", "--no-interactive"], obj=ctx)

        assert result.exit_code == 0

        # Verify one command execution
        assert len(executor.executed_commands) == 1
        command, worktree_path, dangerous, verbose = executor.executed_commands[0]
        assert command == "/erk:plan-implement"
        assert dangerous is False
        assert verbose is False


def test_non_interactive_with_submit_runs_all_commands() -> None:
    """Verify --no-interactive --submit runs all three commands."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(
            implement,
            ["#42", "--no-interactive", "--submit"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify three command executions
        assert len(executor.executed_commands) == 3
        commands = [cmd for cmd, _, _, _ in executor.executed_commands]
        assert commands[0] == "/erk:plan-implement"
        assert commands[1] == "/fast-ci"
        assert commands[2] == "/gt:pr-submit"


def test_script_with_submit_includes_all_commands() -> None:
    """Verify --script --submit succeeds and creates script file."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--script", "--submit"], obj=ctx)

        assert result.exit_code == 0

        # Script should be created (output contains script path)
        assert "erk-implement-" in result.output
        assert ".sh" in result.output


def test_dry_run_shows_execution_mode() -> None:
    """Verify --dry-run shows execution mode."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Test with interactive mode (default)
        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Execution mode: interactive" in result.output

        # Test with non-interactive mode
        result = runner.invoke(implement, ["#42", "--dry-run", "--no-interactive"], obj=ctx)

        assert result.exit_code == 0
        assert "Execution mode: non-interactive" in result.output


def test_dry_run_shows_command_sequence() -> None:
    """Verify --dry-run shows correct command sequence."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Without --submit (single command)
        result = runner.invoke(implement, ["#42", "--dry-run", "--no-interactive"], obj=ctx)

        assert result.exit_code == 0
        assert "Command sequence:" in result.output
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" not in result.output

        # With --submit (three commands)
        result = runner.invoke(
            implement, ["#42", "--dry-run", "--no-interactive", "--submit"], obj=ctx
        )

        assert result.exit_code == 0
        assert "Command sequence:" in result.output
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:pr-submit" in result.output


# YOLO Flag Tests


def test_yolo_flag_sets_all_flags() -> None:
    """Verify --yolo flag is equivalent to --dangerous --submit --no-interactive."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42", "--yolo"], obj=ctx)

        assert result.exit_code == 0

        # Verify three command executions (submit mode)
        assert len(executor.executed_commands) == 3
        commands = [cmd for cmd, _, dangerous, _ in executor.executed_commands]
        assert commands[0] == "/erk:plan-implement"
        assert commands[1] == "/fast-ci"
        assert commands[2] == "/gt:pr-submit"

        # Verify dangerous flag was set for all commands
        for _, _, dangerous, _ in executor.executed_commands:
            assert dangerous is True


def test_yolo_flag_in_dry_run() -> None:
    """Verify --yolo flag works with --dry-run."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--yolo", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify execution mode shown as non-interactive
        assert "Execution mode: non-interactive" in result.output

        # Verify all three commands shown with dangerous flag
        assert result.output.count("--dangerously-skip-permissions") == 3
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:pr-submit" in result.output

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_yolo_flag_conflicts_with_script() -> None:
    """Verify --yolo and --script are mutually exclusive."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # --yolo sets --no-interactive, which conflicts with --script
        result = runner.invoke(implement, ["#42", "--yolo", "--script"], obj=ctx)

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


# Worktree Stacking Tests


def test_implement_from_worktree_stacks_on_current_branch_with_graphite() -> None:
    """When Graphite enabled and on feature branch, stack on current branch."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},  # On feature branch
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            use_graphite=True,  # Graphite enabled
        )

        result = runner.invoke(implement, ["123", "--script"], obj=ctx)

        assert result.exit_code == 0
        # Branch is created via git, stacking uses feature-branch as base


def test_implement_from_worktree_uses_trunk_without_graphite() -> None:
    """When Graphite disabled, always use trunk as base even if on feature branch."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},  # On feature branch
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            use_graphite=False,  # Graphite disabled
        )

        result = runner.invoke(implement, ["123", "--script"], obj=ctx)

        assert result.exit_code == 0
        # Branch is created with main as base (not feature-branch)


def test_implement_from_trunk_uses_trunk_with_graphite() -> None:
    """When on trunk branch, use trunk as base regardless of Graphite."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},  # On trunk branch
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            use_graphite=True,  # Graphite enabled
        )

        result = runner.invoke(implement, ["123", "--script"], obj=ctx)

        assert result.exit_code == 0
        # Branch is created with main as base (we're on trunk)


# Relative Path Preservation Tests


def test_interactive_mode_preserves_relative_path_from_subdirectory() -> None:
    """Verify interactive mode passes relative path when run from subdirectory.

    When user runs `erk implement #42` from worktree/src/lib/, the relative path
    'src/lib' should be captured and passed to execute_interactive so that Claude
    can start in the corresponding subdirectory of the new worktree.
    """
    import os

    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a subdirectory structure in the worktree
        subdir = env.cwd / "src" / "lib"
        subdir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # Include worktree info so compute_relative_path_in_worktree works
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)

        # Build context with cwd set to the subdirectory
        ctx = build_workspace_test_context(
            env, git=git, plan_store=store, claude_executor=executor, cwd=subdir
        )

        # Change to subdirectory before invoking command
        os.chdir(subdir)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0

        # Verify execute_interactive was called with relative path
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath = executor.interactive_calls[0]
        assert dangerous is False
        assert command == "/erk:plan-implement"
        # The relative path from worktree root to src/lib should be passed
        assert target_subpath == Path("src/lib")


def test_interactive_mode_no_relative_path_from_worktree_root() -> None:
    """Verify interactive mode passes None when run from worktree root.

    When user runs `erk implement #42` from the worktree root itself,
    no relative path should be passed (target_subpath=None).
    """
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        # Run from worktree root (default in erk_isolated_fs_env)
        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0

        # Verify target_subpath is None when at worktree root
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath = executor.interactive_calls[0]
        assert target_subpath is None


def test_interactive_mode_preserves_relative_path_from_plan_file() -> None:
    """Verify plan file mode also preserves relative path when run from subdirectory."""
    import os

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a subdirectory structure
        subdir = env.cwd / "docs"
        subdir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        executor = FakeClaudeExecutor(claude_available=True)

        # Create plan file at worktree root
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        # Build context with cwd set to the subdirectory
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor, cwd=subdir)

        # Change to subdirectory before invoking command
        os.chdir(subdir)

        result = runner.invoke(implement, [str(plan_file)], obj=ctx)

        assert result.exit_code == 0

        # Verify execute_interactive was called with relative path
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath = executor.interactive_calls[0]
        assert target_subpath == Path("docs")


# Project-Aware .impl/ Placement Tests (Monorepo Support)


def test_impl_folder_created_at_project_root_in_monorepo() -> None:
    """Verify .impl/ is created at project root (where .erk/project.toml exists).

    When running `erk implement` from within a project subdirectory in a monorepo,
    the .impl/ folder should be created at the project root, not the worktree root.
    This ensures Claude starts in the correct context for the project.
    """
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a monorepo project structure:
        # repo/
        #   python_modules/
        #     my-project/
        #       .erk/
        #         project.toml  <-- Project marker
        #       src/
        #         main.py
        project_path = env.cwd / "python_modules" / "my-project"
        project_path.mkdir(parents=True)
        (project_path / ".erk").mkdir()
        (project_path / ".erk" / "project.toml").write_text("", encoding="utf-8")

        subdir = project_path / "src"
        subdir.mkdir()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)

        # Build context with cwd inside the project
        ctx = build_workspace_test_context(
            env, git=git, plan_store=store, claude_executor=executor, cwd=subdir
        )

        # Change to project subdirectory before invoking command
        os.chdir(subdir)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1
        worktree_path = git.added_worktrees[0][0]

        # Verify .impl/ was created at project root (python_modules/my-project/),
        # NOT at worktree root
        project_impl_path = worktree_path / "python_modules" / "my-project" / ".impl"
        assert project_impl_path.exists(), f".impl/ should be at project root: {project_impl_path}"
        assert (project_impl_path / "plan.md").exists()
        assert (project_impl_path / "progress.md").exists()
        assert (project_impl_path / "issue.json").exists()

        # Verify .impl/ was NOT created at worktree root
        worktree_root_impl = worktree_path / ".impl"
        assert not worktree_root_impl.exists(), (
            f".impl/ should NOT be at worktree root when in a project: {worktree_root_impl}"
        )


def test_impl_folder_created_at_worktree_root_when_no_project() -> None:
    """Verify .impl/ is created at worktree root when no project context exists.

    When running `erk implement` from a directory that is not inside a project
    (no .erk/project.toml in parent directories), the .impl/ folder should be
    created at the worktree root as before.
    """
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a simple subdirectory (no project marker)
        subdir = env.cwd / "src" / "lib"
        subdir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)

        # Build context with cwd in subdirectory (but no project)
        ctx = build_workspace_test_context(
            env, git=git, plan_store=store, claude_executor=executor, cwd=subdir
        )

        # Change to subdirectory before invoking command
        os.chdir(subdir)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0

        # Verify worktree was created
        assert len(git.added_worktrees) == 1
        worktree_path = git.added_worktrees[0][0]

        # Verify .impl/ was created at worktree root (default behavior)
        worktree_root_impl = worktree_path / ".impl"
        assert worktree_root_impl.exists(), (
            f".impl/ should be at worktree root when no project: {worktree_root_impl}"
        )
        assert (worktree_root_impl / "plan.md").exists()


def test_impl_folder_plan_file_mode_respects_project_context() -> None:
    """Verify plan file mode also creates .impl/ at project root in monorepo."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a monorepo project structure
        project_path = env.cwd / "packages" / "my-app"
        project_path.mkdir(parents=True)
        (project_path / ".erk").mkdir()
        (project_path / ".erk" / "project.toml").write_text("", encoding="utf-8")

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        executor = FakeClaudeExecutor(claude_available=True)

        # Create plan file at worktree root
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        # Build context with cwd inside the project
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor, cwd=project_path)

        # Change to project directory before invoking command
        os.chdir(project_path)

        result = runner.invoke(implement, [str(plan_file)], obj=ctx)

        assert result.exit_code == 0

        # Verify worktree was created
        assert len(git.added_worktrees) == 1
        worktree_path = git.added_worktrees[0][0]

        # Verify .impl/ was created at project root within worktree
        project_impl_path = worktree_path / "packages" / "my-app" / ".impl"
        assert project_impl_path.exists(), f".impl/ should be at project root: {project_impl_path}"
        assert (project_impl_path / "plan.md").read_text(encoding="utf-8") == plan_content
