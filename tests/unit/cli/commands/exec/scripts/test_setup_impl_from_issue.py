"""Tests for erk exec setup-impl-from-issue command."""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.setup_impl_from_issue import (
    _get_current_branch,
    setup_impl_from_issue,
)
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.git.remote_ops.types import PullRebaseError
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR


class TestGetCurrentBranch:
    """Tests for the _get_current_branch helper function."""

    def test_returns_branch_name(self, tmp_path: Path) -> None:
        """Returns current branch name when on a branch."""
        git = FakeGit(current_branches={tmp_path: "feature-branch"})
        result = _get_current_branch(git, tmp_path)
        assert result == "feature-branch"

    def test_raises_on_detached_head(self, tmp_path: Path) -> None:
        """Raises ClickException when in detached HEAD state."""
        git = FakeGit(current_branches={tmp_path: None})
        with pytest.raises(click.ClickException) as exc_info:
            _get_current_branch(git, tmp_path)
        assert "detached HEAD" in str(exc_info.value)


class TestSetupImplFromIssueValidation:
    """Tests for validation in setup-impl-from-issue command."""

    def test_missing_issue_shows_error(self, tmp_path: Path) -> None:
        """Command fails gracefully when issue cannot be found."""
        runner = CliRunner()

        # Create a minimal context
        ctx = ErkContext.for_test(cwd=tmp_path)

        # The command requires a GitHub issue that doesn't exist
        # This test verifies the error handling for missing issues
        result = runner.invoke(
            setup_impl_from_issue,
            ["999999"],  # Non-existent issue number
            obj=ctx,
            catch_exceptions=False,
        )

        # Command should fail with exit code 1
        # (actual behavior depends on whether we're mocking GitHub or not)
        # For this unit test, we're primarily testing the CLI interface
        assert result.exit_code != 0 or "error" in result.output.lower()


class TestSetupImplFromIssueNoImplFlag:
    """Tests for --no-impl flag in setup-impl-from-issue command."""

    def test_no_impl_flag_is_accepted(self, tmp_path: Path) -> None:
        """Verify --no-impl flag is accepted by the CLI.

        Note: Full integration testing of --no-impl behavior requires
        refactoring the command to use DI for GitHubIssues. This test
        just verifies the flag is accepted without syntax errors.
        """
        runner = CliRunner()

        # Create a minimal context
        ctx = ErkContext.for_test(cwd=tmp_path)

        # The command will fail because it can't reach GitHub,
        # but we verify the flag is accepted without a click.UsageError
        result = runner.invoke(
            setup_impl_from_issue,
            ["42", "--no-impl"],
            obj=ctx,
        )

        # Verify no usage error (flag was accepted)
        assert "Usage:" not in result.output, "--no-impl flag should be accepted"
        assert "Error: No such option:" not in result.output, "--no-impl should be a valid option"

        # The command should fail due to GitHub access, not CLI parsing
        # (exit code 1 is expected when GitHub fails)
        assert result.exit_code == 1


class TestSetupImplFromIssueBranchManager:
    """Tests verifying BranchManager is used for branch creation."""

    def test_uses_branch_manager_with_graphite_tracking(self, tmp_path: Path) -> None:
        """Verify command uses BranchManager which enables Graphite tracking.

        When Graphite is enabled (FakeGraphite, not GraphiteDisabled), branch
        creation should go through GraphiteBranchManager which calls
        graphite.track_branch() after creating the git branch.

        This test verifies the behavior change from the PR that switched from
        direct git.create_branch() to branch_manager.create_branch().
        """
        # Arrange: Create plan issue with erk-plan label
        now = datetime.now(UTC)
        plan_issue = IssueInfo(
            number=42,
            title="Test Plan",
            body="# Plan Content\n\nSome plan details here.",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/42",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-author",
        )
        fake_issues = FakeGitHubIssues(issues={42: plan_issue})

        # Configure FakeGit with:
        # - current branch on main
        # - empty list of local branches (so branch doesn't exist)
        fake_git = FakeGit(
            current_branches={tmp_path: "main"},
            local_branches=[],
        )

        # Configure FakeGraphite to track calls
        fake_graphite = FakeGraphite()

        # Create test context with all fakes
        # Use context_for_test directly to pass graphite parameter
        ctx = context_for_test(
            github_issues=fake_issues,
            git=fake_git,
            graphite=fake_graphite,
            cwd=tmp_path,
            repo_root=tmp_path,
        )

        # Act: Invoke command with --no-impl to skip folder creation
        runner = CliRunner()
        result = runner.invoke(
            setup_impl_from_issue,
            ["42", "--no-impl"],
            obj=ctx,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Verify output contains valid JSON
        # The output may have status messages before the JSON line
        # Extract the JSON line (last non-empty line that starts with '{')
        output_lines = result.output.strip().split("\n")
        json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
        output = json.loads(json_line)
        assert output["success"] is True
        assert output["issue_number"] == 42

        # Assert: Graphite track_branch was called (key assertion)
        # This verifies the branch was created through BranchManager,
        # not direct git calls
        assert len(fake_graphite.track_branch_calls) == 1
        tracked_call = fake_graphite.track_branch_calls[0]
        # track_branch_calls are (cwd, branch_name, parent_branch) tuples
        assert tracked_call[0] == tmp_path  # repo_root
        assert tracked_call[1].startswith("P42-")  # branch_name starts with issue prefix
        assert tracked_call[2] == "main"  # parent_branch is main

    def test_checks_out_newly_created_branch(self, tmp_path: Path) -> None:
        """Verify setup-impl-from-issue checks out the newly created branch.

        This test ensures that after creating a new branch, the command also
        checks it out so that subsequent operations happen on the new branch,
        not the parent branch.

        Previously, only create_branch was called without checkout_branch,
        causing implementation changes to end up on the wrong branch.
        """
        # Arrange: Create plan issue with erk-plan label
        now = datetime.now(UTC)
        plan_issue = IssueInfo(
            number=99,
            title="Branch Checkout Test",
            body="# Plan Content\n\nVerify checkout after branch creation.",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/99",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-author",
        )
        fake_issues = FakeGitHubIssues(issues={99: plan_issue})

        # Configure FakeGit with:
        # - current branch on a feature branch (to test stacking)
        # - empty list of local branches (so new branch doesn't exist)
        fake_git = FakeGit(
            current_branches={tmp_path: "parent-feature"},
            local_branches=[],
        )

        # Configure FakeGraphite to track calls
        fake_graphite = FakeGraphite()

        # Create test context with all fakes
        ctx = context_for_test(
            github_issues=fake_issues,
            git=fake_git,
            graphite=fake_graphite,
            cwd=tmp_path,
            repo_root=tmp_path,
        )

        # Act: Invoke command with --no-impl to skip folder creation
        runner = CliRunner()
        result = runner.invoke(
            setup_impl_from_issue,
            ["99", "--no-impl"],
            obj=ctx,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Branch was created
        assert len(fake_git.created_branches) == 1
        created_branch = fake_git.created_branches[0]
        # (cwd, branch_name, start_point, force)
        branch_name = created_branch[1]
        assert branch_name.startswith("P99-")

        # Assert: The newly created branch was checked out (KEY ASSERTION)
        # This is the bug fix - previously checkout_branch was never called
        # after GraphiteBranchManager.create_branch, which does temporary checkouts
        # internally but restores the original branch at the end.
        #
        # GraphiteBranchManager.create_branch does:
        #   1. Checkout new branch (to track with Graphite)
        #   2. Restore original branch (parent-feature)
        # Then setup_impl_from_issue should:
        #   3. Checkout the new branch again
        #
        # So we verify the LAST checkout is to the new branch
        assert len(fake_git.checked_out_branches) >= 1, "At least one checkout should occur"
        final_checkout = fake_git.checked_out_branches[-1]
        # checked_out_branches are (cwd, branch) tuples
        assert final_checkout[0] == tmp_path
        assert final_checkout[1] == branch_name  # Last checkout is to the new branch

    def test_reuses_current_branch_when_already_on_matching_branch(self, tmp_path: Path) -> None:
        """When already on a P{issue}-* branch, reuse it instead of creating a new one.

        This prevents the issue where remote implementation workflows re-run
        with an issue number argument and create a new orphan branch, causing:
        - PR branch orphaned (commits on old branch, PR points to new branch)
        - CI failures from branch mismatch

        The fix detects when we're already on a branch matching P{issue_number}-*
        and reuses it without creating a new branch.
        """
        # Arrange: Already on a branch for issue 77
        existing_branch = "P77-fix-remote-implementation-01-24-2229"

        now = datetime.now(UTC)
        plan_issue = IssueInfo(
            number=77,
            title="Fix Remote Implementation",
            body="# Plan Content\n\nFix the remote implementation workflow.",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/77",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-author",
        )
        fake_issues = FakeGitHubIssues(issues={77: plan_issue})

        # Configure FakeGit with current branch already matching the issue
        fake_git = FakeGit(
            current_branches={tmp_path: existing_branch},
            local_branches=[existing_branch],
        )

        fake_graphite = FakeGraphite()

        ctx = context_for_test(
            github_issues=fake_issues,
            git=fake_git,
            graphite=fake_graphite,
            cwd=tmp_path,
            repo_root=tmp_path,
        )

        # Act: Invoke command with issue number (simulating remote workflow behavior)
        runner = CliRunner()
        result = runner.invoke(
            setup_impl_from_issue,
            ["77", "--no-impl"],
            obj=ctx,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: No branch was created (KEY ASSERTION)
        assert len(fake_git.created_branches) == 0, (
            "Should NOT create a new branch when already on matching P{issue}-* branch"
        )

        # Assert: No Graphite track was called
        assert len(fake_graphite.track_branch_calls) == 0, (
            "Should NOT track a branch when reusing existing branch"
        )

        # Assert: Output shows reuse message
        assert f"Already on branch for issue #77: {existing_branch}" in result.output

        # Assert: Output JSON has the existing branch name
        output_lines = result.output.strip().split("\n")
        json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
        output = json.loads(json_line)
        assert output["success"] is True
        assert output["branch"] == existing_branch
        assert output["issue_number"] == 77


# =============================================================================
# Draft-PR plan branch sync tests
# =============================================================================


def _make_draft_pr_context(
    tmp_path: Path,
    plan_branch: str,
    *,
    fake_git: FakeGit | None = None,
    fake_graphite: FakeGraphite | None = None,
) -> tuple[ErkContext, int]:
    """Create an ErkContext configured for draft-PR plan backend with shared FakeGitHub.

    The FakeGitHub is shared between the DraftPRPlanBackend and the context,
    so that both plan_backend.get_provider_name() and github.get_pr() work.

    Returns (context, pr_number).
    """
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime())
    plan_result = backend.create_plan(
        repo_root=tmp_path,
        title="My Plan",
        content="# Plan\n\nImplement something.",
        labels=("erk-plan",),
        metadata={"branch_name": plan_branch},
    )
    pr_number = int(plan_result.plan_id)

    if fake_git is None:
        fake_git = FakeGit(current_branches={tmp_path: "master"})
    if fake_graphite is None:
        fake_graphite = FakeGraphite()

    ctx = context_for_test(
        github=fake_github,
        git=fake_git,
        graphite=fake_graphite,
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )
    return ctx, pr_number


def test_draft_pr_plan_uses_plan_branch_name(tmp_path: Path) -> None:
    """Draft-PR plan with branch_name checks out the plan branch and syncs with remote."""
    plan_branch = "my-plan-branch-02-19"
    fake_git = FakeGit(
        current_branches={tmp_path: "master"},
        local_branches={tmp_path: [plan_branch]},
    )
    ctx, pr_number = _make_draft_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        [str(pr_number), "--no-impl"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Fetch was called for the plan branch
    assert fake_git.fetched_branches == [("origin", plan_branch)]

    # Branch was checked out
    assert (tmp_path, plan_branch) in fake_git.checked_out_branches

    # Pull-rebase was called to sync with remote
    assert fake_git.pull_rebase_calls == [(tmp_path, "origin", plan_branch)]

    # Output contains the plan branch name
    output_lines = result.output.strip().split("\n")
    json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    assert output["branch"] == plan_branch


def test_draft_pr_plan_already_on_plan_branch(tmp_path: Path) -> None:
    """Already on the plan branch — no checkout needed, just fetch and pull-rebase."""
    plan_branch = "my-plan-branch-02-19"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},  # Already on the plan branch
    )
    ctx, pr_number = _make_draft_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        [str(pr_number), "--no-impl"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Fetch was called
    assert fake_git.fetched_branches == [("origin", plan_branch)]

    # No checkout (already on the plan branch)
    assert all(b != plan_branch for _, b in fake_git.checked_out_branches)

    # Pull-rebase was called to sync
    assert fake_git.pull_rebase_calls == [(tmp_path, "origin", plan_branch)]

    assert f"Already on plan branch '{plan_branch}'" in result.output


def test_draft_pr_plan_sync_failure_reports_error(tmp_path: Path) -> None:
    """Pull-rebase failure exits with code 1 and reports error JSON."""
    plan_branch = "my-plan-branch-02-19"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},  # Already on the plan branch
        pull_rebase_error=PullRebaseError(message="Rebase conflict"),
    )
    ctx, pr_number = _make_draft_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        [str(pr_number), "--no-impl"],
        obj=ctx,
    )

    assert result.exit_code == 1

    # Error JSON is present in output
    json_lines = [line for line in result.output.strip().split("\n") if line.startswith("{")]
    assert json_lines, "Expected JSON error output in command output"
    error_data = json.loads(json_lines[0])
    assert error_data["success"] is False
    assert error_data["error"] == "pull_rebase_failed"
    assert "Rebase conflict" in error_data["message"]


def test_issue_plan_without_branch_name_uses_p_prefix(tmp_path: Path) -> None:
    """Issue-based plan without BRANCH_NAME in header_fields uses P{issue}-... naming."""
    now = datetime.now(UTC)
    plan_issue = IssueInfo(
        number=42,
        title="Test Plan",
        body="# Plan Content\n\nSome plan details here.",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-author",
    )
    fake_issues = FakeGitHubIssues(issues={42: plan_issue})

    fake_git = FakeGit(
        current_branches={tmp_path: "master"},
    )
    fake_graphite = FakeGraphite()

    ctx = context_for_test(
        github_issues=fake_issues,
        git=fake_git,
        graphite=fake_graphite,
        cwd=tmp_path,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        ["42", "--no-impl"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # No remote fetch or sync for issue-based plans
    assert len(fake_git.fetched_branches) == 0
    assert len(fake_git.pull_rebase_calls) == 0

    # Branch name uses P{issue}-... prefix
    output_lines = result.output.strip().split("\n")
    json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    assert output["branch"].startswith("P42-")


# =============================================================================
# Draft-PR plan: .erk/impl-context/ local file reading
# =============================================================================


def test_draft_pr_reads_from_impl_context_when_present(tmp_path: Path) -> None:
    """Draft-PR plan reads plan content from .erk/impl-context/ after checkout."""
    plan_branch = "plan-test-local-read-02-20"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},
    )
    ctx, pr_number = _make_draft_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    # Create .erk/impl-context/ with plan content (simulates committed files on branch)
    impl_context_dir = tmp_path / IMPL_CONTEXT_DIR
    impl_context_dir.mkdir(parents=True)
    (impl_context_dir / "plan.md").write_text("# Local Plan\n\nFrom impl-context.", encoding="utf-8")
    (impl_context_dir / "ref.json").write_text(
        json.dumps({"provider": "github-draft-pr", "title": "Local Plan", "objective_id": 42}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        [str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # .impl/ folder was created with local plan content (not PR body content)
    impl_plan = tmp_path / ".impl" / "plan.md"
    assert impl_plan.exists()
    assert "Local Plan" in impl_plan.read_text(encoding="utf-8")
    assert "From impl-context" in impl_plan.read_text(encoding="utf-8")

    # .erk/impl-context/ was cleaned up
    assert not impl_context_dir.exists()

    # Output JSON has correct metadata
    output_lines = result.output.strip().split("\n")
    json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
    output = json.loads(json_line)
    assert output["success"] is True
    assert output["plan_title"] == "Local Plan"


def test_draft_pr_reads_objective_id_from_ref_json(tmp_path: Path) -> None:
    """objective_id from ref.json is passed to save_plan_ref."""
    plan_branch = "plan-test-objective-02-20"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},
    )
    ctx, pr_number = _make_draft_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    # Create .erk/impl-context/ with objective_id
    impl_context_dir = tmp_path / IMPL_CONTEXT_DIR
    impl_context_dir.mkdir(parents=True)
    (impl_context_dir / "plan.md").write_text("# Plan with objective", encoding="utf-8")
    (impl_context_dir / "ref.json").write_text(
        json.dumps({"provider": "github-draft-pr", "title": "Plan", "objective_id": 99}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        [str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify plan-ref.json in .impl/ has the objective_id
    plan_ref_path = tmp_path / ".impl" / "plan-ref.json"
    assert plan_ref_path.exists()
    plan_ref = json.loads(plan_ref_path.read_text(encoding="utf-8"))
    assert plan_ref["objective_id"] == 99
    assert plan_ref["provider"] == "github-draft-pr"


def test_draft_pr_falls_back_to_pr_body_when_no_impl_context(tmp_path: Path) -> None:
    """When .erk/impl-context/ doesn't exist, extract plan from PR body."""
    plan_branch = "plan-test-fallback-02-20"
    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},
    )
    ctx, pr_number = _make_draft_pr_context(tmp_path, plan_branch, fake_git=fake_git)

    # No .erk/impl-context/ directory — triggers fallback to PR body extraction

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        [str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # .impl/ folder was created with plan content extracted from PR body
    impl_plan = tmp_path / ".impl" / "plan.md"
    assert impl_plan.exists()
    # The PR body was created via _make_draft_pr_context with content "# Plan\n\nImplement something."
    assert "Plan" in impl_plan.read_text(encoding="utf-8")
    assert "Implement something" in impl_plan.read_text(encoding="utf-8")


def test_draft_pr_pr_not_found_reports_error(tmp_path: Path) -> None:
    """When the PR doesn't exist, report an error."""
    # Create a DraftPRPlanBackend but don't create any PR
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime())

    fake_git = FakeGit(current_branches={tmp_path: "master"})

    ctx = context_for_test(
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl_from_issue,
        ["9999"],
        obj=ctx,
    )

    assert result.exit_code == 1
    json_lines = [line for line in result.output.strip().split("\n") if line.startswith("{")]
    assert json_lines
    error_data = json.loads(json_lines[0])
    assert error_data["success"] is False
    assert "not found" in error_data["message"].lower()
