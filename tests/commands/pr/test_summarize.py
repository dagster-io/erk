"""Tests for erk pr summarize command.

These tests verify the CLI layer behavior of the summarize command.
The command generates an AI-powered commit message and amends the current commit.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.metadata.plan_header import (
    format_plan_content_comment,
    format_plan_header_body,
)
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_summarize_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "claude.com/download" in result.output


def test_pr_summarize_fails_when_no_commits_ahead() -> None:
    """Test that command fails when branch has no commits ahead of parent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 0},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "No commits ahead" in result.output
        assert "Make a commit first" in result.output


def test_pr_summarize_fails_when_multiple_commits() -> None:
    """Test that command fails when multiple commits exist (needs squash)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 3},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "Multiple commits (3)" in result.output
        assert "gt squash" in result.output


def test_pr_summarize_success_amends_commit() -> None:
    """Test successful summarize generates message and amends commit."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+new content"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        github = FakeGitHub(authenticated=True)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add awesome feature\n\nThis PR adds an awesome new feature.",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0
        assert "Commit message updated" in result.output
        assert "Add awesome feature" in result.output

        # Verify commit was amended (amend_commit adds or updates in git.commits)
        assert len(git.commits) == 1
        commit_message = git.commits[0].message
        assert "Add awesome feature" in commit_message
        assert "awesome new feature" in commit_message


def test_pr_summarize_uses_graphite_parent() -> None:
    """Test that summarize uses Graphite parent branch, not trunk.

    Stack: main (trunk) → branch-1 → branch-2 (current)
    Expected: Diff computed against branch-1, not main
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "branch-1", "branch-2"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "branch-2"},
            commits_ahead={(env.cwd, "branch-1"): 1},
            diff_to_branch={(env.cwd, "branch-1"): "diff --git a/file2.py b/file2.py\n+feature 2"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "branch-2": BranchMetadata(
                    name="branch-2",
                    parent="branch-1",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "branch-1": BranchMetadata(
                    name="branch-1",
                    parent="main",
                    children=["branch-2"],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["branch-1"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        github = FakeGitHub(authenticated=True)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add feature 2\n\nThis adds feature 2.",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0

        # Verify the prompt was called with correct branches
        assert len(claude_executor.prompt_calls) == 1
        prompt, system_prompt = claude_executor.prompt_calls[0]
        # Should contain branch-1 as parent (Graphite parent)
        assert "branch-1" in prompt
        assert "branch-2" in prompt


def test_pr_summarize_fails_when_message_generation_fails() -> None:
    """Test that command fails when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+content"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_error="Claude CLI execution failed",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output


def _make_issue_info(
    *,
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create an IssueInfo for testing."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _make_plan_issue_body(
    *,
    plan_comment_id: int,
    objective_issue: int | None,
) -> str:
    """Create a plan issue body with standard defaults."""
    return format_plan_header_body(
        created_at="2024-01-01T00:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=plan_comment_id,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=objective_issue,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )


def _make_summarize_fakes(
    env,
    *,
    branch_name: str,
    fake_github_issues: FakeGitHubIssues,
):
    """Create standard fakes for summarize plan context tests."""
    git = FakeGit(
        git_common_dirs={env.cwd: env.git_dir},
        repository_roots={env.cwd: env.git_dir},
        local_branches={env.cwd: ["main", branch_name]},
        default_branches={env.cwd: "main"},
        trunk_branches={env.git_dir: "main"},
        current_branches={env.cwd: branch_name},
        commits_ahead={(env.cwd, "main"): 1},
        diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+content"},
    )
    graphite = FakeGraphite(
        authenticated=True,
        branches={
            branch_name: BranchMetadata(
                name=branch_name,
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha=None,
            ),
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=[branch_name],
                is_trunk=True,
                commit_sha=None,
            ),
        },
    )
    github = FakeGitHub(authenticated=True, issues_gateway=fake_github_issues)
    claude_executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output="Fix the bug\n\nThis fixes the bug.",
    )
    return git, graphite, github, claude_executor


def test_pr_summarize_shows_plan_context_with_objective() -> None:
    """Test that plan context with objective is displayed during summarize."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_body = _make_plan_issue_body(plan_comment_id=1000, objective_issue=200)
        plan_issue = _make_issue_info(number=123, title="Plan: Fix bug", body=plan_body)
        objective_issue = _make_issue_info(
            number=200, title="Improve CI Reliability", body="Objective body"
        )
        comment = IssueComment(
            id=1000,
            body=format_plan_content_comment("# Plan\nFix the bug."),
            url="https://github.com/test-owner/test-repo/issues/123#issuecomment-1000",
            author="testuser",
        )
        fake_github_issues = FakeGitHubIssues(
            issues={123: plan_issue, 200: objective_issue},
            comments_with_urls={123: [comment]},
        )

        git, graphite, github, claude_executor = _make_summarize_fakes(
            env, branch_name="P123-fix-bug", fake_github_issues=fake_github_issues
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0
        assert "Incorporating plan from issue #123" in result.output
        assert "Linked to Objective #200: Improve CI Reliability" in result.output


def test_pr_summarize_shows_plan_context_without_objective() -> None:
    """Test that plan context without objective shows plan but not objective line."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        plan_body = _make_plan_issue_body(plan_comment_id=1000, objective_issue=None)
        plan_issue = _make_issue_info(number=123, title="Plan: Fix bug", body=plan_body)
        comment = IssueComment(
            id=1000,
            body=format_plan_content_comment("# Plan\nFix the bug."),
            url="https://github.com/test-owner/test-repo/issues/123#issuecomment-1000",
            author="testuser",
        )
        fake_github_issues = FakeGitHubIssues(
            issues={123: plan_issue},
            comments_with_urls={123: [comment]},
        )

        git, graphite, github, claude_executor = _make_summarize_fakes(
            env, branch_name="P123-fix-bug", fake_github_issues=fake_github_issues
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0
        assert "Incorporating plan from issue #123" in result.output
        assert "Linked to" not in result.output


def test_pr_summarize_shows_no_linked_plan() -> None:
    """Test that branches without plan issue show 'No linked plan found'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        fake_github_issues = FakeGitHubIssues()

        git, graphite, github, claude_executor = _make_summarize_fakes(
            env, branch_name="feature", fake_github_issues=fake_github_issues
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0
        assert "No linked plan found" in result.output
