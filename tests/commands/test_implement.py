"""Tests for unified implement command."""

import os
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk.cli.commands.implement_shared import detect_target_type, normalize_model_name
from erk.cli.config import LoadedConfig
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
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
    target_info = detect_target_type("#123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_plain_number_as_issue() -> None:
    """Test that plain numbers are treated as GitHub issue numbers."""
    target_info = detect_target_type("123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_issue_url() -> None:
    """Test detection of GitHub issue URLs."""
    url = "https://github.com/user/repo/issues/456"
    target_info = detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "456"


def test_detect_issue_url_with_path() -> None:
    """Test detection of GitHub issue URLs with additional path."""
    url = "https://github.com/user/repo/issues/789#issuecomment-123"
    target_info = detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "789"


def test_detect_relative_numeric_file() -> None:
    """Test that numeric files with ./ prefix are treated as file paths."""
    target_info = detect_target_type("./123")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_plain_and_prefixed_numbers_equivalent() -> None:
    """Test that plain and prefixed numbers both resolve to issue numbers."""
    result_plain = detect_target_type("809")
    result_prefixed = detect_target_type("#809")
    assert result_plain.target_type == result_prefixed.target_type == "issue_number"
    assert result_plain.issue_number == result_prefixed.issue_number == "809"


def test_detect_file_path() -> None:
    """Test detection of file paths."""
    target_info = detect_target_type("./my-feature-plan.md")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_detect_file_path_with_special_chars() -> None:
    """Test detection of file paths with special characters."""
    target_info = detect_target_type("/path/to/my-plan.md")
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
        assert "Assigned" in result.output
        # Slot-based path
        assert "erk-managed-wt-" in result.output

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
        assert "Assigned" in result.output
        # Slot-based path
        assert "erk-managed-wt-" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        impl_path = worktree_paths[0] / ".impl"
        assert impl_path.exists()
        assert (impl_path / "plan.md").exists()
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
        assert "Assigned" in result.output
        assert len(git.added_worktrees) == 1

        # Verify issue.json contains correct issue number
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        issue_json_path = worktree_paths[0] / ".impl" / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json_content


def test_implement_assigns_to_pool_slot() -> None:
    """Test that implement assigns worktree to a pool slot."""
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
        # Should show slot assignment message instead of worktree creation
        assert "Assigned" in result.output
        assert "erk-managed-wt-" in result.output

        # Verify worktree was created in slot path
        assert len(git.added_worktrees) == 1
        worktree_path, _ = git.added_worktrees[0]
        assert "erk-managed-wt-" in str(worktree_path)


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
        assert "Assigned" in result.output
        assert "erk-managed-wt-" in result.output

        # Verify worktree created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists with plan content
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        impl_plan = worktree_paths[0] / ".impl" / "plan.md"
        assert impl_plan.exists()
        assert impl_plan.read_text(encoding="utf-8") == plan_content

        # Verify original plan file deleted (move semantics)
        assert not plan_file.exists()


def test_implement_from_plan_file_assigns_to_slot() -> None:
    """Test implementing from plan file assigns to a pool slot."""
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

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        # Should show slot assignment message
        assert "Assigned" in result.output
        assert "erk-managed-wt-" in result.output

        # Verify worktree was created in slot path
        worktree_path, _ = git.added_worktrees[0]
        assert "erk-managed-wt-" in str(worktree_path)


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


def test_implement_works_from_pool_slot() -> None:
    """Test that implement can be run from within a pool slot.

    Unlike the previous behavior which blocked running from within pool slots,
    the slot-first implementation allows this and assigns to a different slot.
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
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Simulate running from within a pool slot by having the command work normally
        # (The old behavior would have blocked this with an error)
        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        # Should succeed - slot-first allows running from anywhere
        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1


def test_implement_force_flag_accepted() -> None:
    """Test that --force flag is accepted by the command.

    The --force flag allows auto-unassigning the oldest slot when the pool
    is full. This test verifies the flag is properly parsed and doesn't
    cause errors during normal operation.
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
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Use --force flag (should work without issue when pool isn't full)
        result = runner.invoke(implement, ["#42", "--script", "--force"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output
        assert len(git.added_worktrees) == 1


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
        assert "Assigned" in result.output

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
        assert "Assigned" in result.output

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
        assert "Assigned" in result.output

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
        assert "Assigned" in result.output
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
        assert "Assigned" in result.output
        # Verify worktree was created
        assert len(git.added_worktrees) == 1


def test_implement_from_issue_uses_gt_create_with_graphite() -> None:
    """Test that new branches are created via gt create when use_graphite=True.

    When Graphite is enabled and implementing from an issue where the branch doesn't
    exist yet, the code path uses `gt create` via subprocess. This subprocess call
    can't be easily unit tested, so this test documents the expected behavior and
    verifies that the test infrastructure notes this limitation.

    Note: Integration tests should verify `gt create` is called with correct args.
    For unit testing, we verify the graphite-disabled path works (see
    test_implement_uses_git_when_graphite_disabled).
    """
    # This test documents that `gt create` is used for new branches with Graphite.
    # The actual subprocess call requires integration testing.
    # See: test_implement_uses_git_when_graphite_disabled for the non-Graphite path.
    pass


def test_implement_from_issue_skips_tracking_existing_branch_with_graphite() -> None:
    """Test track_branch is NOT called when re-implementing with an existing branch.

    When implementing an issue where the branch ALREADY exists locally,
    we do NOT re-track the branch since it was already tracked when first created.

    This scenario occurs when:
    1. A previous implementation attempt created the branch (and tracked it)
    2. The worktree was deleted but branch remains
    3. User runs `erk implement` again for the same issue
    """

    plan_issue = _create_sample_plan_issue("500")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Pre-create the branch that will be used for this issue
        # Branch name format: P<issue_number>-<sanitized-title>-<timestamp>
        existing_branch = "P500-add-authentication-feature-01-15-1430"

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            # Branch already exists from previous implementation attempt
            local_branches={env.cwd: ["main", existing_branch]},
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

        # Assert: track_branch was NOT called because branch already existed
        # (when branch exists, it was already tracked when first created)
        assert len(fake_graphite.track_branch_calls) == 0, (
            f"Expected 0 track_branch calls for existing branch, got "
            f"{len(fake_graphite.track_branch_calls)}: {fake_graphite.track_branch_calls}"
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
        assert "Assigned" in result.output

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

        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        # Slot-based path
        assert "erk-managed-wt-" in str(worktree_path)
        assert dangerous is False
        assert command == "/erk:plan-implement"
        # No relative path preservation when running from worktree root
        assert target_subpath is None
        assert model is None


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
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert dangerous is True
        assert command == "/erk:plan-implement"
        assert model is None


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
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert "erk-managed-wt-" in str(worktree_path)
        assert dangerous is False
        assert command == "/erk:plan-implement"
        assert model is None

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
        command, worktree_path, dangerous, verbose, model = executor.executed_commands[0]
        assert command == "/erk:plan-implement"
        assert dangerous is False
        assert verbose is False
        assert model is None


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
        commands = [cmd for cmd, _, _, _, _ in executor.executed_commands]
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
        commands = [cmd for cmd, _, dangerous, _, _ in executor.executed_commands]
        assert commands[0] == "/erk:plan-implement"
        assert commands[1] == "/fast-ci"
        assert commands[2] == "/gt:pr-submit"

        # Verify dangerous flag was set for all commands
        for _, _, dangerous, _, _ in executor.executed_commands:
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
    """When Graphite enabled and on feature branch, stack on current branch.

    The key verification is that the parent_branch in track_branch is the
    current branch (feature-branch), not trunk. This test uses file mode
    with a new branch (not pre-existing) so track_branch is called.
    """

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            # Note: "new-feature" branch does NOT exist yet
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},  # On feature branch
        )
        fake_graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=fake_graphite,
            use_graphite=True,  # Graphite enabled
        )

        # Create plan file - branch name will be derived as "new-feature"
        plan_file = env.cwd / "new-feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify track_branch was called with feature-branch as parent (stacking behavior)
        assert len(fake_graphite.track_branch_calls) == 1
        _cwd, branch_name, parent_branch = fake_graphite.track_branch_calls[0]
        assert branch_name == "new-feature"
        assert parent_branch == "feature-branch", (
            f"Expected parent 'feature-branch' (stacking), got: {parent_branch}"
        )


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
    """When on trunk branch, use trunk as base regardless of Graphite.

    The key verification is that the parent_branch in track_branch is trunk (main).
    This test uses file mode with a new branch (not pre-existing) so track_branch is called.
    """

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            # Note: "new-feature" branch does NOT exist yet
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},  # On trunk branch
        )
        fake_graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=fake_graphite,
            use_graphite=True,  # Graphite enabled
        )

        # Create plan file - branch name will be derived as "new-feature"
        plan_file = env.cwd / "new-feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify track_branch was called with main as parent (trunk-based)
        assert len(fake_graphite.track_branch_calls) == 1
        _cwd, branch_name, parent_branch = fake_graphite.track_branch_calls[0]
        assert branch_name == "new-feature"
        assert parent_branch == "main", f"Expected parent 'main' (trunk), got: {parent_branch}"


# Relative Path Preservation Tests


def test_interactive_mode_preserves_relative_path_from_subdirectory() -> None:
    """Verify interactive mode passes relative path when run from subdirectory.

    When user runs `erk implement #42` from worktree/src/lib/, the relative path
    'src/lib' should be captured and passed to execute_interactive so that Claude
    can start in the corresponding subdirectory of the new worktree.
    """
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
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert dangerous is False
        assert command == "/erk:plan-implement"
        # The relative path from worktree root to src/lib should be passed
        assert target_subpath == Path("src/lib")
        assert model is None


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
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert target_subpath is None
        assert model is None


def test_interactive_mode_preserves_relative_path_from_plan_file() -> None:
    """Verify plan file mode also preserves relative path when run from subdirectory."""
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
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert target_subpath == Path("docs")
        assert model is None


# Model Normalization Tests


def testnormalize_model_name_full_names() -> None:
    """Test normalizing full model names (haiku, sonnet, opus)."""
    assert normalize_model_name("haiku") == "haiku"
    assert normalize_model_name("sonnet") == "sonnet"
    assert normalize_model_name("opus") == "opus"


def testnormalize_model_name_aliases() -> None:
    """Test normalizing model name aliases (h, s, o)."""
    assert normalize_model_name("h") == "haiku"
    assert normalize_model_name("s") == "sonnet"
    assert normalize_model_name("o") == "opus"


def testnormalize_model_name_case_insensitive() -> None:
    """Test that model names are case-insensitive."""
    assert normalize_model_name("HAIKU") == "haiku"
    assert normalize_model_name("Sonnet") == "sonnet"
    assert normalize_model_name("OPUS") == "opus"
    assert normalize_model_name("H") == "haiku"
    assert normalize_model_name("S") == "sonnet"
    assert normalize_model_name("O") == "opus"


def testnormalize_model_name_none() -> None:
    """Test that None input returns None."""
    assert normalize_model_name(None) is None


def testnormalize_model_name_invalid() -> None:
    """Test that invalid model names raise ClickException."""
    import click
    import pytest

    with pytest.raises(click.ClickException) as exc_info:
        normalize_model_name("invalid")
    assert "Invalid model: 'invalid'" in str(exc_info.value)
    assert "Valid options:" in str(exc_info.value)


# Model Flag Integration Tests


def test_model_flag_in_interactive_mode() -> None:
    """Verify --model flag is passed to executor in interactive mode."""
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

        result = runner.invoke(implement, ["#42", "--model", "opus"], obj=ctx)

        assert result.exit_code == 0

        # Verify model was passed to execute_interactive
        assert len(executor.interactive_calls) == 1
        _, _, _, _, model = executor.interactive_calls[0]
        assert model == "opus"


def test_model_flag_short_form_in_interactive_mode() -> None:
    """Verify -m short form flag is passed to executor in interactive mode."""
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

        result = runner.invoke(implement, ["#42", "-m", "sonnet"], obj=ctx)

        assert result.exit_code == 0

        # Verify model was passed to execute_interactive
        assert len(executor.interactive_calls) == 1
        _, _, _, _, model = executor.interactive_calls[0]
        assert model == "sonnet"


def test_model_alias_in_interactive_mode() -> None:
    """Verify model alias (h, s, o) is expanded in interactive mode."""
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

        result = runner.invoke(implement, ["#42", "-m", "h"], obj=ctx)

        assert result.exit_code == 0

        # Verify model alias was expanded to full name
        assert len(executor.interactive_calls) == 1
        _, _, _, _, model = executor.interactive_calls[0]
        assert model == "haiku"


def test_model_flag_in_non_interactive_mode() -> None:
    """Verify --model flag is passed to executor in non-interactive mode."""
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

        result = runner.invoke(implement, ["#42", "--no-interactive", "--model", "opus"], obj=ctx)

        assert result.exit_code == 0

        # Verify model was passed to execute_command
        assert len(executor.executed_commands) == 1
        _, _, _, _, model = executor.executed_commands[0]
        assert model == "opus"


def test_model_flag_in_script_mode() -> None:
    """Verify --model flag is included in generated script."""
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

        result = runner.invoke(implement, ["#42", "--script", "--model", "sonnet"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify --model flag is present in the generated command
        assert "--model sonnet" in script_content


def test_model_flag_in_dry_run() -> None:
    """Verify --model flag is shown in dry-run output."""
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
            implement, ["#42", "--dry-run", "--no-interactive", "--model", "opus"], obj=ctx
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify --model flag is shown in the command sequence
        assert "--model opus" in result.output

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_invalid_model_flag() -> None:
    """Verify invalid model names are rejected."""
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

        result = runner.invoke(implement, ["#42", "--model", "invalid-model"], obj=ctx)

        assert result.exit_code != 0
        assert "Invalid model" in result.output


# Pre-existing Slot Directory Tests


def test_implement_uses_checkout_when_slot_directory_exists() -> None:
    """Test that implement uses checkout_branch (not add_worktree) when slot dir exists.

    This is a regression test for a bug where `erk implement` would fail with
    "directory already exists" when:
    1. A managed slot directory exists on disk (from pool initialization)
    2. But find_inactive_slot() returns None (slot not tracked in pool state)

    The fix tracks initialized slots in state.slots so find_inactive_slot returns them.
    When find_inactive_slot returns an initialized slot, checkout_branch is used.
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
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Pre-create the slot directory to simulate pool initialization
        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        # Track the slot in pool state so find_inactive_slot() returns it
        # This simulates proper pool initialization where slots are tracked
        from erk.core.worktree_pool import PoolState, SlotInfo, save_pool_state

        init_state = PoolState.test(
            pool_size=4,
            slots=(SlotInfo(name="erk-managed-wt-01", last_objective_issue=None),),
        )
        save_pool_state(env.repo.pool_json_path, init_state)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Key assertion: checkout_branch should be called (not add_worktree)
        # because the slot was returned by find_inactive_slot()
        assert len(git.checked_out_branches) == 1, (
            f"Expected 1 checkout_branch call, got {len(git.checked_out_branches)}"
        )
        assert len(git.added_worktrees) == 0, (
            f"Expected 0 add_worktree calls (slot was inactive), got {len(git.added_worktrees)}: "
            f"{git.added_worktrees}"
        )


# Pool Size Config Override Tests


def test_implement_respects_config_pool_size_over_stored_state() -> None:
    """Test that pool_size from config overrides the stored pool_size in pool.json.

    This is a regression test for a bug where:
    1. Pool state was created with pool_size=4 (the default)
    2. User configured pool_size=16 in config.toml
    3. When pool had 4 assignments, `erk implement` would fail with "Pool is full (4 slots)"
       even though config allowed 16 slots

    The fix ensures config's pool_size is used when loading existing pool state.
    """
    plan_issue = _create_sample_plan_issue("99")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo = env.repo
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"99": plan_issue})

        # Create pool state with pool_size=4 and 4 assignments (full pool at old size)
        old_pool_size = 4
        assignments = tuple(
            SlotAssignment(
                slot_name=f"erk-managed-wt-{i:02d}",
                branch_name=f"existing-branch-{i}",
                assigned_at="2024-01-01T00:00:00+00:00",
                worktree_path=repo.worktrees_dir / f"erk-managed-wt-{i:02d}",
            )
            for i in range(1, old_pool_size + 1)
        )
        full_state = PoolState(
            version="1.0",
            pool_size=old_pool_size,  # Pool thinks max is 4
            slots=(),
            assignments=assignments,
        )
        save_pool_state(repo.pool_json_path, full_state)

        # Configure context with pool_size=16 (larger than stored)
        new_pool_size = 16
        local_config = LoadedConfig.test(pool_size=new_pool_size)
        ctx = build_workspace_test_context(
            env, git=git, plan_store=store, local_config=local_config
        )

        # Run implement - should succeed by using config's pool_size
        result = runner.invoke(implement, ["#99", "--script"], obj=ctx)

        # Should succeed, not fail with "Pool is full"
        assert result.exit_code == 0, f"Expected success but got: {result.output}"
        assert "Assigned" in result.output

        # Should have assigned to slot 5 (first available after slots 1-4)
        assert "erk-managed-wt-05" in result.output


# Uncommitted Changes Detection Tests


def test_implement_fails_with_uncommitted_changes_in_slot() -> None:
    """Test that implement fails with friendly error when slot has uncommitted changes.

    When a pre-existing slot directory has uncommitted changes that would be
    overwritten by git checkout, we should detect this BEFORE attempting checkout
    and provide actionable remediation steps instead of letting git fail with
    an ugly traceback.
    """
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Pre-create the slot directory with uncommitted changes
        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # Configure the slot worktree to have uncommitted changes
            file_statuses={slot_dir: ([], ["modified_file.py"], [])},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # Track the slot in pool state so find_inactive_slot() returns it
        # This simulates proper pool initialization where slots are tracked
        from erk.core.worktree_pool import PoolState, SlotInfo, save_pool_state

        init_state = PoolState.test(
            pool_size=4,
            slots=(SlotInfo(name="erk-managed-wt-01", last_objective_issue=None),),
        )
        save_pool_state(env.repo.pool_json_path, init_state)

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        # Should fail with friendly error message
        assert result.exit_code != 0

        # Verify error message contains remediation options
        assert "uncommitted changes" in result.output
        assert "erk-managed-wt-01" in result.output
        assert "git stash" in result.output
        assert "git commit" in result.output
        assert "erk slot unassign" in result.output

        # Verify no worktree operations were attempted after the check
        assert len(git.added_worktrees) == 0
        assert len(git.checked_out_branches) == 0


# Same-Slot Stacking Tests


def test_implement_from_managed_slot_stacks_on_current_branch() -> None:
    """Test that implementing from within a managed slot stacks on current branch.

    When running `erk implement` from within a managed slot:
    1. Detects we're in a managed slot
    2. Creates new branch stacked on current branch
    3. Updates slot assignment to new branch
    4. Does NOT consume a new slot
    """

    plan_issue = _create_sample_plan_issue("200")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Create a slot worktree directory
        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        # Configure git to recognize the slot as a managed worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_dir: env.git_dir},
            local_branches={env.cwd: ["main", "existing-feature"]},
            default_branches={env.cwd: "main"},
            current_branches={slot_dir: "existing-feature"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_dir, branch="existing-feature", is_root=False),
                ]
            },
        )
        store, _ = create_plan_store_with_plans({"200": plan_issue})
        fake_graphite = FakeGraphite()

        # Create initial pool state with the slot assigned
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="existing-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        # Build context with cwd set to the slot directory
        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            graphite=fake_graphite,
            use_graphite=True,
            cwd=slot_dir,
        )

        # Run implement from within the slot
        result = runner.invoke(implement, ["#200", "--script"], obj=ctx)

        assert result.exit_code == 0, f"Expected success but got: {result.output}"

        # Verify stacking message
        assert "Stacking" in result.output or "Stacked" in result.output

        # Verify a new branch was created
        assert len(git.created_branches) == 1

        # Verify the branch was tracked with the current branch as parent
        assert len(fake_graphite.track_branch_calls) == 1
        _cwd, new_branch, parent_branch = fake_graphite.track_branch_calls[0]
        assert parent_branch == "existing-feature"

        # Verify NO new worktrees were created (same slot reused)
        assert len(git.added_worktrees) == 0

        # Verify the branch was checked out in the slot
        assert len(git.checked_out_branches) == 1


def test_implement_from_managed_slot_requires_clean_worktree() -> None:
    """Test that same-slot stacking fails if there are uncommitted changes.

    Users must commit their work before starting a new stacked implementation
    to avoid losing changes.
    """
    plan_issue = _create_sample_plan_issue("201")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Create a slot worktree directory
        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        # Configure git with uncommitted changes in the slot
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_dir: env.git_dir},
            local_branches={env.cwd: ["main", "existing-feature"]},
            default_branches={env.cwd: "main"},
            current_branches={slot_dir: "existing-feature"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_dir, branch="existing-feature", is_root=False),
                ]
            },
            # Slot has uncommitted changes
            file_statuses={slot_dir: ([], ["modified.py"], [])},
        )
        store, _ = create_plan_store_with_plans({"201": plan_issue})

        # Create initial pool state with the slot assigned
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="existing-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            cwd=slot_dir,
        )

        result = runner.invoke(implement, ["#201", "--script"], obj=ctx)

        # Should fail with error about uncommitted changes
        assert result.exit_code != 0
        assert "uncommitted changes" in result.output
        assert "Commit your changes" in result.output
        assert "git commit" in result.output

        # Verify no branches were created
        assert len(git.created_branches) == 0


def test_implement_from_managed_slot_dry_run() -> None:
    """Test that dry-run mode shows same-slot stacking information."""
    plan_issue = _create_sample_plan_issue("202")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_dir: env.git_dir},
            local_branches={env.cwd: ["main", "existing-feature"]},
            default_branches={env.cwd: "main"},
            current_branches={slot_dir: "existing-feature"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_dir, branch="existing-feature", is_root=False),
                ]
            },
        )
        store, _ = create_plan_store_with_plans({"202": plan_issue})

        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="existing-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            cwd=slot_dir,
        )

        result = runner.invoke(implement, ["#202", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify same-slot stacking info is shown
        assert "stack" in result.output.lower()
        assert "erk-managed-wt-01" in result.output
        assert "existing-feature" in result.output

        # Verify no changes were made
        assert len(git.created_branches) == 0
        assert len(git.checked_out_branches) == 0


def test_implement_from_managed_slot_updates_pool_state() -> None:
    """Test that same-slot stacking updates the pool state with new branch."""
    plan_issue = _create_sample_plan_issue("203")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        slot_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot_dir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir, slot_dir: env.git_dir},
            local_branches={env.cwd: ["main", "existing-feature"]},
            default_branches={env.cwd: "main"},
            current_branches={slot_dir: "existing-feature"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_dir, branch="existing-feature", is_root=False),
                ]
            },
        )
        store, _ = create_plan_store_with_plans({"203": plan_issue})

        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="existing-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
            cwd=slot_dir,
        )

        result = runner.invoke(implement, ["#203", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Load and verify pool state was updated
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None

        # Should still have only 1 assignment (same slot, different branch)
        assert len(updated_state.assignments) == 1

        assignment = updated_state.assignments[0]
        assert assignment.slot_name == "erk-managed-wt-01"
        # Branch name should be updated to new branch
        assert assignment.branch_name != "existing-feature"
        # Worktree path should be the same
        assert assignment.worktree_path == slot_dir


def test_implement_not_from_slot_uses_new_slot() -> None:
    """Test that implementing from outside a managed slot uses a new slot.

    This verifies the normal behavior still works when NOT running from a slot.
    """
    plan_issue = _create_sample_plan_issue("204")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create an existing slot assignment
        env.setup_repo_structure()
        slot1_dir = env.repo.worktrees_dir / "erk-managed-wt-01"
        slot1_dir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"204": plan_issue})

        # Create pool state with one existing assignment
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="other-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=slot1_dir,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        # Run from the main worktree (not a slot)
        ctx = build_workspace_test_context(
            env,
            git=git,
            plan_store=store,
        )

        result = runner.invoke(implement, ["#204", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Should assign to a NEW slot (slot 02)
        assert "erk-managed-wt-02" in result.output

        # Load pool state to verify
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None
        assert len(updated_state.assignments) == 2  # Original + new
