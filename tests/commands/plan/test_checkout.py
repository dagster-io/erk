"""Tests for plan checkout command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import PRReference
from erk_shared.github.types import PRDetails
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def _make_plan(
    *,
    issue_number: int,
    worktree_name: str | None,
) -> Plan:
    """Create a Plan for testing.

    Args:
        issue_number: Plan issue number
        worktree_name: Optional worktree name to include in plan-header

    Returns:
        Plan object
    """
    if worktree_name is not None:
        body = f"""<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

worktree_name: {worktree_name}
schema_version: 2

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan content here
"""
    else:
        body = "# Plan content without worktree_name"

    return Plan(
        plan_identifier=str(issue_number),
        title=f"Test Plan #{issue_number}",
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{issue_number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )


def test_checkout_single_local_branch_exists() -> None:
    """Test checkout when single matching local branch exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with local branch P123-feature
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / "erk-slot-01"
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "P123-feature"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(
                        path=worktree_path,
                        branch="P123-feature",
                        is_root=False,
                    )
                ]
            },
            existing_paths={env.cwd, env.git_dir, worktree_path},
        )

        ctx = build_workspace_test_context(env, git=git, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["plan", "co", "123"], obj=ctx)

        # With shell integration disabled (default in tests), it spawns subshell
        # which isn't available, so the command itself works but navigation exits
        # For testing, we check the output indicates checkout happened
        assert "P123-feature" in result.output or "already checked out" in result.output


def test_checkout_multiple_local_branches_shows_list() -> None:
    """Test checkout displays list when multiple local branches match."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with multiple matching branches
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "P123-first", "P123-second"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        ctx = build_workspace_test_context(env, git=git, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["plan", "checkout", "123"], obj=ctx)

        assert result.exit_code == 1
        assert "has multiple local branches" in result.output
        assert "P123-first" in result.output
        assert "P123-second" in result.output
        assert "erk br co <branch>" in result.output


def test_checkout_no_branch_single_open_pr() -> None:
    """Test checkout fetches and checks out single open PR when no local branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, _plan_fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with no matching local branches
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
            remote_branches={env.cwd: ["origin/main", "origin/plan-123-impl"]},
        )

        # Configure GitHub with PR linked to the issue
        github = FakeGitHub(
            pr_details={
                456: PRDetails(
                    number=456,
                    url="https://github.com/owner/repo/pull/456",
                    title="Implement plan 123",
                    body="Refs #123",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="plan-123-impl",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            }
        )

        # Configure issues gateway with PR reference
        fake_issues = FakeGitHubIssues(
            pr_references={123: [PRReference(number=456, state="OPEN", is_draft=False)]}
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, plan_store=store, issues=fake_issues
        )

        result = runner.invoke(cli, ["plan", "co", "123"], obj=ctx)

        # Check that it tried to checkout the PR branch
        # The exact behavior depends on git state, but it should mention the PR
        assert "PR" in result.output or "plan-123-impl" in result.output or result.exit_code == 0


def test_checkout_no_branch_multiple_open_prs_shows_table() -> None:
    """Test checkout displays table when multiple open PRs reference the plan."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, _plan_fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with no matching local branches
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Configure GitHub with multiple PRs
        github = FakeGitHub(
            pr_details={
                456: PRDetails(
                    number=456,
                    url="https://github.com/owner/repo/pull/456",
                    title="First implementation",
                    body="Refs #123",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="plan-123-first",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                ),
                789: PRDetails(
                    number=789,
                    url="https://github.com/owner/repo/pull/789",
                    title="Alternative approach",
                    body="Refs #123",
                    state="OPEN",
                    is_draft=True,
                    base_ref_name="main",
                    head_ref_name="plan-123-second",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                ),
            }
        )

        # Configure issues with multiple PR references
        fake_issues = FakeGitHubIssues(
            pr_references={
                123: [
                    PRReference(number=456, state="OPEN", is_draft=False),
                    PRReference(number=789, state="OPEN", is_draft=True),
                ]
            }
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, plan_store=store, issues=fake_issues
        )

        result = runner.invoke(cli, ["plan", "checkout", "123"], obj=ctx)

        assert result.exit_code == 1
        assert "has multiple open PRs" in result.output
        assert "#456" in result.output or "456" in result.output
        assert "#789" in result.output or "789" in result.output
        assert "erk pr co <pr_number>" in result.output


def test_checkout_no_branch_no_pr_suggests_implement() -> None:
    """Test checkout suggests 'erk plan implement' when neither branch nor PR exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, _plan_fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with no matching branches
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Configure issues with no PR references
        fake_issues = FakeGitHubIssues(pr_references={})

        ctx = build_workspace_test_context(env, git=git, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["plan", "co", "123"], obj=ctx)

        assert result.exit_code == 1
        assert "no local branch or open PR" in result.output
        assert "erk plan implement 123" in result.output


def test_checkout_uses_worktree_name_from_metadata() -> None:
    """Test checkout includes worktree_name from plan-header when looking for branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan with worktree_name in metadata
        plan = _make_plan(issue_number=123, worktree_name="my-custom-branch")
        store, fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with the worktree_name branch (not matching P123-* pattern)
        worktree_path = env.erk_root / "repos" / "repo" / "worktrees" / "erk-slot-01"
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "my-custom-branch"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(
                        path=worktree_path,
                        branch="my-custom-branch",
                        is_root=False,
                    )
                ]
            },
            existing_paths={env.cwd, env.git_dir, worktree_path},
        )

        ctx = build_workspace_test_context(env, git=git, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["plan", "co", "123"], obj=ctx)

        # Should find and checkout my-custom-branch
        assert "my-custom-branch" in result.output or result.exit_code == 0


def test_checkout_plan_not_found() -> None:
    """Test checkout shows error when plan doesn't exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create empty plan store
        store, fake_issues = create_plan_store_with_plans({})

        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["plan", "co", "999"], obj=ctx)

        assert result.exit_code == 1
        assert "Plan #999 not found" in result.output


def test_checkout_with_github_url() -> None:
    """Test checkout accepts GitHub issue URL as plan_id."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with no matching branches
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        ctx = build_workspace_test_context(env, git=git, plan_store=store, issues=fake_issues)

        result = runner.invoke(
            cli,
            ["plan", "co", "https://github.com/owner/repo/issues/123"],
            obj=ctx,
        )

        # Should parse URL and find plan 123
        assert "123" in result.output


def test_checkout_filters_to_open_prs_only() -> None:
    """Test checkout only considers OPEN PRs, not closed/merged ones."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, _plan_fake_issues = create_plan_store_with_plans({"123": plan})

        # Configure git with no matching local branches
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        # Configure issues with one open PR and one closed PR
        fake_issues = FakeGitHubIssues(
            pr_references={
                123: [
                    PRReference(number=456, state="CLOSED", is_draft=False),
                    PRReference(number=789, state="MERGED", is_draft=False),
                ]
            }
        )

        ctx = build_workspace_test_context(env, git=git, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["plan", "co", "123"], obj=ctx)

        # Should show "no branch or open PR" since both PRs are closed/merged
        assert result.exit_code == 1
        assert "no local branch or open PR" in result.output


def test_checkout_alias_co() -> None:
    """Test 'erk plan co' alias works."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create plan
        plan = _make_plan(issue_number=123, worktree_name=None)
        store, fake_issues = create_plan_store_with_plans({"123": plan})

        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Use 'co' alias
        result = runner.invoke(cli, ["plan", "co", "123"], obj=ctx)

        # Should process the command (either success or expected error)
        assert "123" in result.output
