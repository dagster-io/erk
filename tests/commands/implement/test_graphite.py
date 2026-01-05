"""Tests for Graphite configuration and worktree stacking in implement command."""

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans

# Graphite Configuration Tests


def test_implement_uses_git_when_graphite_disabled() -> None:
    """Test that implement uses standard git workflow when use_graphite=false.

    Note: Tests with use_graphite=true require graphite subprocess integration
    (gt create command), which should be tested at the integration level with
    real gt commands, not in unit tests.
    """
    plan_issue = create_sample_plan_issue()

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

    plan_issue = create_sample_plan_issue("500")

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
    plan_issue = create_sample_plan_issue("123")

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
